# Workflow manager for predefined workflow execution
import asyncio
import uuid
import json
import os
import requests
from typing import Dict, Any, List, Optional
from fastmcp import Client
from planner.llm_client import call_llm
from utils.mcp_utils import extract_tool_result

LOGGING_SERVICE_URL = os.getenv("LOGGING_SERVICE_URL", "http://logging-service:8200")

def _log_system_event(level: str, message: str, details: Dict[str, Any] = None, session_id: str = None):
    """Send system log to logging service (non-blocking)"""
    try:
        log_payload = {
            "level": level,
            "service": "orchestrator",
            "message": message,
            "details": details,
            "session_id": session_id
        }
        requests.post(
            f"{LOGGING_SERVICE_URL}/logs/system",
            json=log_payload,
            timeout=2
        )
    except Exception as e:
        print(f"[Workflow] Warning: Failed to send system log: {e}")

class WorkflowNode:
    """Represents a node in a workflow"""

    def __init__(self, node_id: str, node_type: str, config: Dict[str, Any]):
        self.id = node_id
        self.type = node_type  # "agent" or "tool"
        self.config = config
        self.status = "pending"
        self.result = None
        self.error = None

class WorkflowManager:
    """
    Manages workflow-based execution where user defines the flow structure.
    """

    def __init__(self, workflow_id: str, mcp_url: str):
        self.workflow_id = workflow_id
        self.mcp_url = mcp_url
        self.nodes = {}  # node_id -> WorkflowNode
        self.edges = []  # [(from_id, to_id), ...]
        self.dependencies = {}  # node_id -> [dependency_ids]
        self._subscribers = []
        self.execution_state = {}

    def add_node(self, node_id: str, node_type: str, config: Dict[str, Any]):
        """Add a node to the workflow"""
        self.nodes[node_id] = WorkflowNode(node_id, node_type, config)
        self.dependencies[node_id] = []

    def add_edge(self, from_id: str, to_id: str):
        """Add a dependency edge"""
        self.edges.append((from_id, to_id))
        if to_id not in self.dependencies:
            self.dependencies[to_id] = []
        self.dependencies[to_id].append(from_id)

    def subscribe(self):
        """Subscribe to real-time updates"""
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    async def _publish(self, msg):
        """Publish update to all subscribers"""
        for q in list(self._subscribers):
            await q.put(msg)

    async def _fetch_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Fetch the input schema for a specific tool"""
        try:
            async with Client(self.mcp_url) as client:
                tools_result = await client.list_tools()
                for tool in tools_result:
                    if tool.name == tool_name:
                        return tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                return {}
        except Exception as e:
            print(f"Error fetching tool schema: {e}")
            return {}

    async def _transform_input_with_llm(self, node: WorkflowNode, dependency_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to intelligently transform dependency outputs into parameters for the current node.
        """
        tool_name = node.config.get("tool")

        # Fetch the tool's input schema
        tool_schema = await self._fetch_tool_schema(tool_name)

        # Build prompt for LLM
        prompt = f"""You are helping transform data between workflow nodes.

Current Node Tool: {tool_name}
Tool Input Schema: {json.dumps(tool_schema, indent=2)}

Available Data from Previous Nodes:
{json.dumps(dependency_outputs, indent=2)}

Your task: Create the correct parameters for {tool_name} using the available data.
- Match the tool's input schema requirements
- Extract relevant values from the dependency outputs
- Transform or adapt data types if needed
- If a required parameter cannot be satisfied, set it to a reasonable default or null

Respond with ONLY a JSON object containing the parameters:
{{"param1": "value1", "param2": "value2", ...}}
"""

        messages = [
            {"role": "system", "content": "You are an expert at data transformation and API parameter mapping. Always respond with valid JSON only, no explanation."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = call_llm(messages, max_tokens=500)
            # Parse the LLM response
            params = json.loads(response)

            await self._publish({
                "type": "input_transformed",
                "node_id": node.id,
                "tool": tool_name,
                "transformed_params": params
            })

            return params
        except Exception as e:
            print(f"Error in LLM transformation: {e}")
            # Fallback to simple passthrough
            return node.config.get("params", {})

    async def _execute_tool_node(self, node: WorkflowNode) -> Any:
        """Execute a tool node with LLM-powered input transformation and DSPy optimization"""
        tool_name = node.config.get("tool")
        params = node.config.get("params", {})
        original_params = params.copy()

        # Collect outputs from dependency nodes
        dependency_outputs = {}
        for dep_id in self.dependencies.get(node.id, []):
            if dep_id in self.nodes:
                dep_node = self.nodes[dep_id]
                if dep_node.result:
                    dependency_outputs[dep_id] = dep_node.result

        # Use LLM to transform inputs if we have dependencies
        if dependency_outputs:
            resolved_params = await self._transform_input_with_llm(node, dependency_outputs)
        else:
            # No dependencies, use provided params as-is
            resolved_params = params

        # Try to optimize parameters with DSPy
        try:
            from utils.remote_config_manager import get_remote_config_manager
            config_manager = get_remote_config_manager()

            await self._publish({
                "type": "optimization_start",
                "node_id": node.id,
                "tool": tool_name,
                "original_params": resolved_params
            })

            optimized_params = config_manager.enhance_parameters(tool_name, resolved_params, context=[])

            # Log parameter corrections if any were made
            if optimized_params != resolved_params:
                corrections = {}
                for key in set(list(optimized_params.keys()) + list(resolved_params.keys())):
                    if optimized_params.get(key) != resolved_params.get(key):
                        corrections[key] = {
                            "before": resolved_params.get(key),
                            "after": optimized_params.get(key),
                            "reason": "Parameter name mapping" if key not in resolved_params else "Value optimization"
                        }

                await self._publish({
                    "type": "parameters_corrected",
                    "node_id": node.id,
                    "tool": tool_name,
                    "corrections": corrections,
                    "original": resolved_params,
                    "optimized": optimized_params
                })

            resolved_params = optimized_params
        except Exception as opt_error:
            await self._publish({
                "type": "optimization_skipped",
                "node_id": node.id,
                "tool": tool_name,
                "reason": str(opt_error)
            })

        # Execute tool with retry and error recovery
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                await self._publish({
                    "type": "tool_call_attempt",
                    "node_id": node.id,
                    "tool": tool_name,
                    "attempt": attempt + 1,
                    "params": resolved_params
                })

                async with Client(self.mcp_url) as client:
                    result = await client.call_tool(tool_name, resolved_params)

                    output = extract_tool_result(result)

                    await self._publish({
                        "type": "tool_call_success",
                        "node_id": node.id,
                        "tool": tool_name,
                        "attempt": attempt + 1
                    })

                    return output

            except Exception as e:
                last_error = str(e)

                _log_system_event(
                    "WARNING",
                    f"Tool call failed (attempt {attempt + 1}/{max_retries})",
                    details={
                        "node_id": node.id,
                        "tool": tool_name,
                        "attempt": attempt + 1,
                        "error": last_error,
                        "params": resolved_params
                    },
                    session_id=self.workflow_id
                )

                await self._publish({
                    "type": "tool_call_failed",
                    "node_id": node.id,
                    "tool": tool_name,
                    "attempt": attempt + 1,
                    "error": last_error
                })

                # Try error recovery on non-final attempts
                if attempt < max_retries - 1:
                    try:
                        from utils.remote_config_manager import get_remote_config_manager
                        config_manager = get_remote_config_manager()

                        _log_system_event(
                            "INFO",
                            "Attempting error recovery",
                            details={
                                "node_id": node.id,
                                "tool": tool_name,
                                "error": last_error,
                                "original_params": resolved_params
                            },
                            session_id=self.workflow_id
                        )

                        await self._publish({
                            "type": "error_recovery_start",
                            "node_id": node.id,
                            "tool": tool_name,
                            "error": last_error
                        })

                        recovered_params = config_manager.recover_from_error(
                            tool_name,
                            resolved_params,
                            last_error,
                            context=[]
                        )

                        if recovered_params != resolved_params:
                            _log_system_event(
                                "INFO",
                                "Error recovery successful - parameters corrected",
                                details={
                                    "node_id": node.id,
                                    "tool": tool_name,
                                    "original_params": resolved_params,
                                    "recovered_params": recovered_params
                                },
                                session_id=self.workflow_id
                            )

                            await self._publish({
                                "type": "error_recovered",
                                "node_id": node.id,
                                "tool": tool_name,
                                "original_params": resolved_params,
                                "recovered_params": recovered_params,
                                "recovery_action": "Parameter correction based on error pattern"
                            })
                            resolved_params = recovered_params
                        else:
                            _log_system_event(
                                "WARNING",
                                "Error recovery failed - no strategy available",
                                details={
                                    "node_id": node.id,
                                    "tool": tool_name
                                },
                                session_id=self.workflow_id
                            )

                            await self._publish({
                                "type": "error_recovery_failed",
                                "node_id": node.id,
                                "tool": tool_name,
                                "reason": "No recovery strategy available"
                            })
                    except Exception as recovery_error:
                        _log_system_event(
                            "ERROR",
                            "Error recovery encountered exception",
                            details={
                                "node_id": node.id,
                                "tool": tool_name,
                                "recovery_error": str(recovery_error)
                            },
                            session_id=self.workflow_id
                        )

                        await self._publish({
                            "type": "error_recovery_failed",
                            "node_id": node.id,
                            "tool": tool_name,
                            "reason": str(recovery_error)
                        })

        raise Exception(f"Tool execution failed after {max_retries} attempts: {last_error}")

    async def _execute_agent_node(self, node: WorkflowNode) -> Any:
        """Execute an agent node"""
        from agents.base_agent import create_agent

        agent_type = node.config.get("agent_type", "executor")
        goal = node.config.get("goal", "Execute task")
        context = node.config.get("context", {})

        # Add results from dependencies to context
        for dep_id in self.dependencies.get(node.id, []):
            if dep_id in self.nodes:
                dep_node = self.nodes[dep_id]
                if dep_node.result:
                    context[f"{dep_id}_result"] = dep_node.result

        agent = create_agent(agent_type, goal, context)

        # Tool executor for agent
        async def tool_executor(tool_name: str, params: Dict[str, Any]) -> Any:
            temp_node = WorkflowNode(f"temp_{uuid.uuid4().hex[:8]}", "tool", {
                "tool": tool_name,
                "params": params
            })
            return await self._execute_tool_node(temp_node)

        # Run agent and collect results
        final_result = None
        async for update in agent.run(tool_executor, max_iterations=5):
            await self._publish({
                "type": "agent_update",
                "node_id": node.id,
                "update": update
            })
            if update.get("type") == "action_result":
                final_result = update.get("result")

        return final_result

    async def _execute_node(self, node: WorkflowNode):
        """Execute a single workflow node"""
        node.status = "running"
        self.execution_state[node.id] = {
            "status": "running",
            "type": node.type
        }

        _log_system_event(
            "DEBUG",
            f"Node execution started: {node.id}",
            details={
                "node_id": node.id,
                "node_type": node.type,
                "config": node.config
            },
            session_id=self.workflow_id
        )

        await self._publish({
            "type": "node_start",
            "node_id": node.id,
            "node_type": node.type
        })

        try:
            if node.type == "tool":
                result = await self._execute_tool_node(node)
            elif node.type == "agent":
                result = await self._execute_agent_node(node)
            else:
                raise ValueError(f"Unknown node type: {node.type}")

            node.status = "success"
            node.result = result
            self.execution_state[node.id] = {
                "status": "success",
                "type": node.type,
                "result": result
            }

            _log_system_event(
                "INFO",
                f"Node execution completed successfully: {node.id}",
                details={
                    "node_id": node.id,
                    "node_type": node.type,
                    "result_preview": str(result)[:200] if result else None
                },
                session_id=self.workflow_id
            )

            await self._publish({
                "type": "node_complete",
                "node_id": node.id,
                "result": result
            })

        except Exception as e:
            node.status = "failed"
            node.error = str(e)
            self.execution_state[node.id] = {
                "status": "failed",
                "type": node.type,
                "error": str(e)
            }

            _log_system_event(
                "ERROR",
                f"Node execution failed: {node.id}",
                details={
                    "node_id": node.id,
                    "node_type": node.type,
                    "error": str(e)
                },
                session_id=self.workflow_id
            )

            await self._publish({
                "type": "node_error",
                "node_id": node.id,
                "error": str(e)
            })

    async def execute(self):
        """Execute the workflow"""
        _log_system_event(
            "INFO",
            "Workflow execution started",
            details={
                "workflow_id": self.workflow_id,
                "node_count": len(self.nodes),
                "nodes": list(self.nodes.keys())
            },
            session_id=self.workflow_id
        )

        await self._publish({
            "type": "workflow_start",
            "workflow_id": self.workflow_id,
            "nodes": list(self.nodes.keys())
        })

        # Find root nodes (no dependencies)
        ready = [node_id for node_id in self.nodes.keys()
                 if not self.dependencies.get(node_id)]

        completed = set()
        running_tasks = {}

        while ready or running_tasks:
            # Start ready nodes
            for node_id in ready:
                node = self.nodes[node_id]
                task = asyncio.create_task(self._execute_node(node))
                running_tasks[node_id] = task

            ready = []

            if running_tasks:
                # Wait for any task to complete
                done, _ = await asyncio.wait(
                    list(running_tasks.values()),
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Process completed nodes
                for node_id, task in list(running_tasks.items()):
                    if task.done():
                        completed.add(node_id)
                        running_tasks.pop(node_id)

                        # Check children
                        for from_id, to_id in self.edges:
                            if from_id == node_id:
                                # Check if all dependencies of child are met
                                deps = self.dependencies.get(to_id, [])
                                if all(dep_id in completed for dep_id in deps):
                                    if to_id not in completed and to_id not in running_tasks:
                                        ready.append(to_id)

        await self._publish({
            "type": "workflow_complete",
            "workflow_id": self.workflow_id,
            "state": self.execution_state
        })

    def get_summary(self):
        """Get workflow execution summary"""
        return {
            "workflow_id": self.workflow_id,
            "nodes": {node_id: {
                "type": node.type,
                "status": node.status,
                "result": node.result,
                "error": node.error
            } for node_id, node in self.nodes.items()},
            "edges": self.edges,
            "state": self.execution_state
        }

    def to_dict(self) -> dict:
        """Export workflow as a JSON-serializable dictionary"""
        import datetime
        return {
            "workflow_id": self.workflow_id,
            "nodes": [
                {
                    "id": node_id,
                    "type": node.type,
                    "config": node.config
                }
                for node_id, node in self.nodes.items()
            ],
            "edges": [{"from": from_id, "to": to_id} for from_id, to_id in self.edges],
            "metadata": {
                "created_at": getattr(self, 'created_at', datetime.datetime.now().isoformat()),
                "description": getattr(self, 'description', ''),
                "version": "1.0"
            }
        }

    @classmethod
    def from_dict(cls, data: dict, mcp_url: str):
        """Import workflow from a JSON dictionary"""
        workflow_id = data.get("workflow_id", str(uuid.uuid4()))
        manager = cls(workflow_id, mcp_url)

        # Add metadata if present
        metadata = data.get("metadata", {})
        manager.created_at = metadata.get("created_at")
        manager.description = metadata.get("description", '')

        # Add nodes
        for node_data in data.get("nodes", []):
            manager.add_node(
                node_data["id"],
                node_data["type"],
                node_data.get("config", {})
            )

        # Add edges
        for edge in data.get("edges", []):
            manager.add_edge(edge["from"], edge["to"])

        return manager
