# Agent manager for coordinating multiple agents
import asyncio
import uuid
from typing import Dict, Any, Optional
from fastmcp import Client
from agents.base_agent import create_agent
from utils.mcp_utils import extract_tool_result

class AgentManager:
    """
    Manages agent execution and coordinates multiple agents working together.
    """

    def __init__(self, session_id: str, mcp_url: str):
        self.session_id = session_id
        self.mcp_url = mcp_url
        self.agents = []
        self.execution_log = []
        self._subscribers = []

    def subscribe(self):
        """Subscribe to real-time updates"""
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    async def _publish(self, msg):
        """Publish update to all subscribers"""
        for q in list(self._subscribers):
            await q.put(msg)

    async def _tool_executor(self, tool_name: str, params: Dict[str, Any], max_retries: int = 2) -> Any:
        """
        Execute a tool via MCP server with retry logic.
        If tool call fails, uses LLM to correct parameters and retries.
        """
        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                async with Client(self.mcp_url) as client:
                    # Log the attempt
                    start_event = {
                        "type": "tool_call_start",
                        "tool": tool_name,
                        "params": params,
                        "attempt": attempt + 1,
                        "is_retry": attempt > 0
                    }
                    await self._publish(start_event)
                    self.execution_log.append(start_event)

                    result = await client.call_tool(tool_name, params)

                    output = extract_tool_result(result)

                    complete_event = {
                        "type": "tool_call_complete",
                        "tool": tool_name,
                        "result": output,
                        "attempt": attempt + 1,
                        "retry_count": attempt
                    }
                    await self._publish(complete_event)
                    self.execution_log.append(complete_event)

                    return output

            except Exception as e:
                last_error = str(e)
                attempt += 1

                error_event = {
                    "type": "tool_call_error",
                    "tool": tool_name,
                    "error": last_error,
                    "params": params,
                    "attempt": attempt,
                    "will_retry": attempt <= max_retries
                }
                await self._publish(error_event)
                self.execution_log.append(error_event)

                print(f"[TOOL EXECUTOR] Tool {tool_name} failed (attempt {attempt}/{max_retries + 1}): {last_error}")

                # If we've exhausted retries, return error
                if attempt > max_retries:
                    print(f"[TOOL EXECUTOR] Max retries reached for {tool_name}, returning error")
                    return {"error": last_error, "retries_exhausted": True}

                # Use LLM to correct parameters
                print(f"[TOOL EXECUTOR] Attempting to fix parameters with LLM...")
                corrected_params = await self._fix_tool_params_with_llm(
                    tool_name,
                    params,
                    last_error,
                    attempt
                )

                if corrected_params:
                    retry_event = {
                        "type": "tool_call_retry",
                        "tool": tool_name,
                        "attempt": attempt + 1,
                        "previous_params": params,
                        "corrected_params": corrected_params,
                        "error": last_error
                    }
                    await self._publish(retry_event)
                    self.execution_log.append(retry_event)

                    params = corrected_params
                    print(f"[TOOL EXECUTOR] Retrying with corrected params: {corrected_params}")
                else:
                    print(f"[TOOL EXECUTOR] LLM could not correct parameters, returning error")
                    return {"error": last_error, "llm_correction_failed": True}

        # Should not reach here, but just in case
        return {"error": last_error, "max_retries_reached": True}

    async def _fix_tool_params_with_llm(
        self,
        tool_name: str,
        failed_params: Dict[str, Any],
        error_message: str,
        attempt: int
    ) -> Optional[Dict[str, Any]]:
        """
        Use DSPy-optimized LLM to analyze the error and provide corrected parameters.
        """
        try:
            import json

            # Get tool schema
            available_tools = await self._fetch_available_tools()
            tool_schema = None
            for tool in available_tools:
                if tool["name"] == tool_name:
                    tool_schema = tool
                    break

            if not tool_schema:
                print(f"[LLM FIX] Tool {tool_name} not found in available tools")
                return None

            # Try DSPy-optimized recovery first
            try:
                print(f"[LLM FIX] Attempting DSPy-optimized parameter recovery...")
                from utils.dspy_optimizer import get_optimizer

                optimizer = get_optimizer()
                corrected_params = await optimizer.recover_from_error(
                    tool_name=tool_name,
                    tool_schema=tool_schema.get('params_schema', {}),
                    failed_params=failed_params,
                    error_message=error_message
                )

                if corrected_params:
                    print(f"[LLM FIX] ✅ DSPy recovered params for {tool_name}: {corrected_params}")
                    return corrected_params
                else:
                    raise Exception("DSPy returned None")

            except Exception as dspy_error:
                print(f"[LLM FIX] DSPy recovery failed ({dspy_error}), falling back to raw LLM")

                # Fallback to raw LLM
                from planner.llm_client import call_llm

                # Create prompt for LLM
                prompt_messages = [
                    {
                        "role": "system",
                        "content": "You are a parameter correction assistant. Your job is to fix tool parameters that caused errors."
                    },
                    {
                        "role": "user",
                        "content": f"""A tool call failed and needs correction.

Tool: {tool_name}
Description: {tool_schema.get('description', 'No description')}

Parameter Schema:
{json.dumps(tool_schema.get('params_schema', {}), indent=2)}

Failed Parameters:
{json.dumps(failed_params, indent=2)}

Error Message:
{error_message}

Attempt: {attempt}

Please analyze the error and provide ONLY corrected parameters as a JSON object. Do not include any explanation, just output valid JSON that matches the tool's parameter schema.

Example response format:
{{"param1": "corrected_value", "param2": 123}}
"""
                    }
                ]

                # Call LLM
                response = call_llm(prompt_messages, max_tokens=500)
                print(f"[LLM FIX] LLM response: {response}")

                # Try to parse JSON from response
                # Strip markdown code blocks if present
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
                response = response.strip()

                corrected_params = json.loads(response)
                print(f"[LLM FIX] Corrected params: {corrected_params}")
                return corrected_params

        except Exception as e:
            print(f"[LLM FIX] Error fixing parameters with LLM: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _fetch_available_tools(self):
        """Fetch all available tools from MCP server"""
        try:
            async with Client(self.mcp_url) as client:
                tools_result = await client.list_tools()
                # Convert to simple dict format
                tools = []
                for tool in tools_result:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "params_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    })
                return tools
        except Exception as e:
            print(f"Error fetching tools from MCP: {e}")
            return []

    async def run_agent_flow(self, agent_type: str, goal: str, context: Dict[str, Any] = None, selected_tools: list = None):
        """
        Run an agent-based flow where the agent works autonomously.
        selected_tools: Optional list of tool names to filter available tools
        """
        await self._publish({
            "type": "flow_start",
            "flow_type": "agent",
            "agent_type": agent_type,
            "goal": goal
        })

        # Fetch available tools from MCP server
        all_tools = await self._fetch_available_tools()

        # Filter tools if selected_tools is provided
        if selected_tools is not None:
            available_tools = [t for t in all_tools if t["name"] in selected_tools]
            print(f"[AGENT] Filtered tools: {len(available_tools)} of {len(all_tools)} selected")
        else:
            available_tools = all_tools
            print(f"[AGENT] Using all {len(all_tools)} tools")

        await self._publish({
            "type": "tools_discovered",
            "tools_count": len(available_tools),
            "tools": [t["name"] for t in available_tools]
        })

        # Create the agent with available tools
        agent = create_agent(agent_type, goal, context)
        agent.tools = available_tools  # Provide tools to the agent
        self.agents.append(agent)

        # Run the agent
        try:
            async for update in agent.run(self._tool_executor, max_iterations=10):
                # Publish each agent update
                await self._publish(update)
                self.execution_log.append(update)

            await self._publish({
                "type": "flow_complete",
                "session_id": self.session_id,
                "agent": agent_type,
                "memory": agent.memory
            })

        except Exception as e:
            await self._publish({
                "type": "flow_error",
                "error": str(e)
            })

    def get_summary(self):
        """Get execution summary with detailed logs"""
        # Extract key information from execution log
        status = "unknown"
        iterations = 0
        result = None
        thoughts = []
        actions = []
        tool_calls = []
        current_tool_call = None

        for entry in self.execution_log:
            entry_type = entry.get("type")

            if entry_type == "thought":
                iterations = entry.get("iteration", 0) + 1
                decision = entry.get("decision", {})
                thoughts.append({
                    "iteration": entry.get("iteration"),
                    "thoughts": decision.get("thoughts"),
                    "decision": decision.get("decision"),
                    "action": decision.get("action")
                })

            elif entry_type == "action_result":
                result = entry.get("result")
                actions.append({
                    "iteration": entry.get("iteration"),
                    "result": result
                })

            elif entry_type == "tool_call_start":
                # Create new tool call or add attempt to existing
                attempt = entry.get("attempt", 1)
                is_retry = entry.get("is_retry", False)

                if not is_retry:
                    # New tool call
                    current_tool_call = {
                        "tool": entry.get("tool"),
                        "params": entry.get("params"),
                        "status": "started",
                        "attempts": [{
                            "attempt": attempt,
                            "params": entry.get("params"),
                            "status": "started"
                        }]
                    }
                    tool_calls.append(current_tool_call)
                else:
                    # Retry of existing tool call
                    if current_tool_call:
                        current_tool_call["attempts"].append({
                            "attempt": attempt,
                            "params": entry.get("params"),
                            "status": "started"
                        })

            elif entry_type == "tool_call_retry":
                # Add retry information to current tool call
                if current_tool_call:
                    current_tool_call["retries"] = current_tool_call.get("retries", [])
                    current_tool_call["retries"].append({
                        "attempt": entry.get("attempt"),
                        "previous_params": entry.get("previous_params"),
                        "corrected_params": entry.get("corrected_params"),
                        "error": entry.get("error")
                    })

            elif entry_type == "tool_call_complete":
                if current_tool_call:
                    current_tool_call["status"] = "completed"
                    current_tool_call["result"] = entry.get("result")
                    current_tool_call["retry_count"] = entry.get("retry_count", 0)
                    current_tool_call["final_attempt"] = entry.get("attempt", 1)

                    # Update last attempt status
                    if current_tool_call.get("attempts"):
                        current_tool_call["attempts"][-1]["status"] = "completed"
                        current_tool_call["attempts"][-1]["result"] = entry.get("result")

            elif entry_type == "tool_call_error":
                if current_tool_call:
                    error_msg = entry.get("error")
                    will_retry = entry.get("will_retry", False)

                    # Update last attempt with error
                    if current_tool_call.get("attempts"):
                        current_tool_call["attempts"][-1]["status"] = "failed"
                        current_tool_call["attempts"][-1]["error"] = error_msg

                    # If not retrying, mark overall status as failed
                    if not will_retry:
                        current_tool_call["status"] = "failed"
                        current_tool_call["error"] = error_msg

            elif entry_type == "complete":
                status = "completed"
                result = entry.get("result")
                iterations = entry.get("iterations", 0)

            elif entry_type == "loop_detected":
                status = "loop_detected"

        # If we have execution log but no explicit completion, mark as running
        if self.execution_log and status == "unknown":
            status = "running"

        return {
            "session_id": self.session_id,
            "status": status,
            "agents": [{"role": a.role, "goal": a.goal} for a in self.agents],
            "iterations": iterations,
            "result": result,
            "execution_log": {
                "thoughts": thoughts,
                "actions": actions,
                "tool_calls": tool_calls,
                "raw_log": self.execution_log
            }
        }
