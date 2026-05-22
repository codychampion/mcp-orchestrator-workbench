# ExecutionManager: resolves params, calls MCP server, records outputs, publishes updates
import asyncio
import time
from collections import defaultdict
from typing import Dict, Any, Optional

class ExecutionManager:
    def __init__(self, execution_id: str, plan: Dict[str, Any], mcp_url: str, max_concurrency: int = 4):
        self.execution_id = execution_id
        self.plan = plan
        self.mcp_url = mcp_url
        self.max_concurrency = max_concurrency
        # Use HTTP client for tool calls instead of fastMCP client to avoid connection issues
        self.mcp_base_url = mcp_url.replace('/mcp', '')  # Get base URL without /mcp path
        self.nodes_by_id = {n['id']: n for n in plan.get('nodes', [])}
        self.edges = plan.get('edges', [])
        self.deps = defaultdict(set)
        self.children = defaultdict(set)
        for e in self.edges:
            self.deps[e['to']].add(e['from'])
            self.children[e['from']].add(e['to'])
        # execution state
        self.state = {nid: {"status":"pending","output":None,"start":None,"end":None,"elapsed":None} for nid in self.nodes_by_id}
        self.execution_start_time = None
        self._subscribers = []
        self._queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    def summary(self):
        return {"execution_id": self.execution_id, "plan": self.plan, "state": self.state}

    def subscribe(self):
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    async def _publish(self, msg):
        for q in list(self._subscribers):
            await q.put(msg)


    async def _enhance_params_with_llm(self, node_id: str, node: dict, params: dict) -> dict:
        """Use DSPy-optimized LLM to fix parameter names and auto-generate missing required parameters using upstream context"""
        try:
            tool_name = node['tool']
            print(f"[PARAM-ENHANCE] Starting parameter enhancement for {tool_name}")

            # Get tool schema to understand required parameters
            from fastmcp import Client
            print(f"[PARAM-ENHANCE] Connecting to MCP server to get tool schema")
            connect_start = time.time()

            async with asyncio.timeout(10.0):  # 10 second timeout for schema fetch - will raise on timeout
                async with Client(self.mcp_url) as client:
                    connect_time = time.time() - connect_start
                    print(f"[PARAM-ENHANCE] Connected in {connect_time:.2f}s, listing tools")

                    list_start = time.time()
                    tools_result = await client.list_tools()
                    list_time = time.time() - list_start
                    print(f"[PARAM-ENHANCE] Retrieved {len(tools_result)} tools in {list_time:.2f}s")

                    tool_schema = None
                    for tool in tools_result:
                        if tool.name == tool_name:
                            tool_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else None
                            print(f"[PARAM-ENHANCE] Found schema for {tool_name}: {tool_schema}")
                            break

            if not tool_schema:
                print(f"[PARAM-ENHANCE] No schema found for {tool_name}, using params as-is")
                return params  # No schema available, return as-is

            # Check all parameters - both correct and incorrect names
            required_params = tool_schema.get('required', []) if isinstance(tool_schema, dict) else []
            schema_properties = tool_schema.get('properties', {}) if isinstance(tool_schema, dict) else {}
            valid_param_names = set(schema_properties.keys())

            # Check if any current parameters have incorrect names or if required ones are missing
            needs_llm_fix = False
            current_param_names = set(params.keys())

            # Check for invalid parameter names (not in schema)
            invalid_params = current_param_names - valid_param_names
            if invalid_params:
                needs_llm_fix = True
                print(f"[PARAM-ENHANCE] Found invalid parameter names for {tool_name}: {invalid_params}")

            # Check for missing required parameters
            missing_params = [param for param in required_params if param not in params or params[param] is None]
            if missing_params:
                needs_llm_fix = True
                print(f"[PARAM-ENHANCE] Found missing required parameters for {tool_name}: {missing_params}")

            if not needs_llm_fix:
                print(f"[PARAM-ENHANCE] All parameters correct, no LLM enhancement needed")
                return params  # All parameters are correct

            # Gather context from completed nodes
            context_data = []
            for nid, state in self.state.items():
                if state['status'] == 'success' and state.get('output'):
                    output = state['output']
                    context_data.append({
                        'node_id': nid,
                        'tool': self.nodes_by_id[nid]['tool'],
                        'output': output
                    })

            # Try DSPy-optimized enhancement first, fallback to raw LLM
            try:
                print(f"[PARAM-ENHANCE] Attempting DSPy-optimized parameter enhancement...")
                from utils.dspy_optimizer import get_optimizer

                optimizer = get_optimizer()
                corrected_params = await optimizer.enhance_parameters(
                    tool_name=tool_name,
                    tool_schema=tool_schema,
                    current_params=params,
                    execution_context=context_data
                )

                print(f"[PARAM-ENHANCE] ✅ DSPy enhanced parameters for {tool_name}: {corrected_params}")
                return corrected_params

            except Exception as dspy_error:
                print(f"[PARAM-ENHANCE] DSPy enhancement failed ({dspy_error}), falling back to raw LLM")

                # Fallback to raw LLM
                from planner.llm_client import call_llm

                context_str = "\n".join([
                    f"- {ctx['node_id']} ({ctx['tool']}): {str(ctx['output'])[:200]}..."
                    for ctx in context_data
                ])

                prompt = f"""Fix parameter names and generate missing parameters for tool '{tool_name}' based on the execution context.

Tool: {tool_name}
Tool schema properties: {schema_properties}
Valid parameter names: {list(valid_param_names)}
Required parameters: {required_params}

Current parameters (may have incorrect names): {params}
Invalid parameter names found: {list(invalid_params)}
Missing required parameters: {missing_params}

Available context from previous steps:
{context_str if context_data else "No previous execution context available"}

IMPORTANT:
1. Fix any incorrect parameter names by mapping them to the correct schema property names
2. Generate values for any missing required parameters using the available context
3. Extract actual content from template expressions like {{{{node.output.result}}}} when possible
4. Return a COMPLETE parameter set with correct names and values

Based on the tool schema and available context, return the corrected and complete parameter set.
Return ONLY a JSON object with all parameters using correct names.

Example response format:
{{"correct_param_name": "value", "another_param": "value"}}
"""

                messages = [
                    {"role": "system", "content": "You are a helpful assistant that generates tool parameters based on execution context. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]

                llm_start = time.time()
                response = call_llm(messages, max_tokens=300)
                llm_time = time.time() - llm_start
                print(f"[PARAM-ENHANCE] LLM response received in {llm_time:.2f}s")

                try:
                    import json
                    corrected_params = json.loads(response)

                    # Replace all parameters with the LLM-corrected ones
                    if isinstance(corrected_params, dict):
                        print(f"[PARAM-ENHANCE] ✅ LLM corrected parameters for {tool_name}: {corrected_params}")
                        return corrected_params
                    else:
                        print(f"[PARAM-ENHANCE] ⚠️  LLM returned invalid parameter format for {tool_name}: {response}")
                        return params

                except json.JSONDecodeError:
                    print(f"[PARAM-ENHANCE] ⚠️  Failed to parse LLM response for parameter correction: {response}")
                    return params

        except Exception as e:
            print(f"Error in parameter enhancement for {node_id}: {e}")
            return params  # Return original params if enhancement fails

    async def _call_tool(self, node_id: str, node: dict):
        async with self._semaphore:
            self.state[node_id]['status'] = 'running'
            self.state[node_id]['start'] = time.time()
            await self._publish({"node": node_id, "status": "running"})

            print(f"\n[EXECUTOR] {'='*60}")
            print(f"[EXECUTOR] Starting tool call for node: {node_id}")
            print(f"[EXECUTOR] Tool: {node.get('tool')}")
            print(f"[EXECUTOR] {'='*60}")

            # resolve params (enhanced with auto-generation for missing required params)
            params = {}
            for k, v in node.get('params_template', {}).items():
                if isinstance(v, str) and v.startswith('{{') and '}}' in v:
                    # format {{nodeid.output.key}}
                    token = v.strip('{} ')
                    parts = token.split('.')
                    try:
                        src_node = parts[0]
                        field = parts[-1]
                        value = self.state[src_node]['output']
                        # assume output is dict
                        params[k] = value.get(field) if isinstance(value, dict) else value
                    except Exception:
                        params[k] = None
                else:
                    params[k] = v

            print(f"[EXECUTOR] Initial params: {params}")

            # Use LLM to fix and enhance all parameters intelligently
            print(f"[EXECUTOR] Enhancing params with LLM...")
            enhance_start = time.time()
            params = await self._enhance_params_with_llm(node_id, node, params)
            enhance_time = time.time() - enhance_start
            print(f"[EXECUTOR] Params enhanced in {enhance_time:.2f}s: {params}")

            try:
                # Execute tools via FastMCP client - no hardcoded logic
                tool_name = node['tool']
                print(f"[EXECUTOR] Connecting to MCP server at {self.mcp_url}")

                from fastmcp import Client
                connect_start = time.time()

                # Add timeout to prevent hanging - will raise TimeoutError on timeout
                async with asyncio.timeout(30.0):  # 30 second timeout for entire operation
                    async with Client(self.mcp_url) as client:
                        connect_time = time.time() - connect_start
                        print(f"[EXECUTOR] Connected to MCP in {connect_time:.2f}s")
                        print(f"[EXECUTOR] Calling tool '{tool_name}' with params: {params}")

                        call_start = time.time()
                        result = await client.call_tool(tool_name, params)
                        call_time = time.time() - call_start

                        print(f"[EXECUTOR] Tool call completed in {call_time:.2f}s")
                        print(f"[EXECUTOR] Raw result: {result}")

                        # Extract the result content
                        if hasattr(result, 'content') and result.content:
                            if isinstance(result.content, list) and len(result.content) > 0:
                                output = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                            else:
                                output = str(result.content)
                        else:
                            output = str(result)

                        print(f"[EXECUTOR] Extracted output: {output}")

                self.state[node_id]['output'] = {'result': output}
                self.state[node_id]['status'] = 'success'
                print(f"[EXECUTOR] ✅ Node {node_id} completed successfully")

            except Exception as e:
                print(f"[EXECUTOR] ❌ Node {node_id} failed: {e}")
                import traceback
                traceback.print_exc()
                self.state[node_id]['status'] = 'failed'
                self.state[node_id]['output'] = {'error': str(e)}
            finally:
                self.state[node_id]['end'] = time.time()
                if self.state[node_id]['start']:
                    self.state[node_id]['elapsed'] = self.state[node_id]['end'] - self.state[node_id]['start']

                print(f"[EXECUTOR] Node {node_id} took {self.state[node_id]['elapsed']:.2f}s")
                print(f"[EXECUTOR] {'='*60}\n")

                # Calculate total execution time
                total_elapsed = None
                if self.execution_start_time:
                    total_elapsed = time.time() - self.execution_start_time

                await self._publish({
                    "node": node_id,
                    "status": self.state[node_id]['status'],
                    "output": self.state[node_id]['output'],
                    "elapsed": self.state[node_id]['elapsed'],
                    "total_elapsed": total_elapsed
                })

    async def _generate_execution_summary(self):
        """Generate an LLM summary of what was accomplished during execution"""
        from planner.llm_client import call_llm

        # Collect execution data for summary
        execution_data = {
            "total_nodes": len(self.nodes_by_id),
            "successful_nodes": 0,
            "failed_nodes": 0
        }

        node_details = []
        for node_id, state in self.state.items():
            tool = self.nodes_by_id[node_id]["tool"]
            status = state["status"]

            if status == "success":
                execution_data["successful_nodes"] += 1
                output = state.get("output", {}).get("result", "")
                node_details.append(f"- {node_id} ({tool}): {status} -> {str(output)[:100]}...")
            elif status == "failed":
                execution_data["failed_nodes"] += 1
                node_details.append(f"- {node_id} ({tool}): {status}")
            else:
                node_details.append(f"- {node_id} ({tool}): {status}")

        # Create summary prompt
        summary_prompt = f"""Please provide a concise summary of this workflow execution. Focus on what was accomplished and the key results.

Execution Results:
- Total nodes: {execution_data['total_nodes']}
- Successful: {execution_data['successful_nodes']}
- Failed: {execution_data['failed_nodes']}

Node Details:
{chr(10).join(node_details)}

Provide a 2-3 sentence summary of what was accomplished."""

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes workflow execution results concisely."},
                {"role": "user", "content": summary_prompt}
            ]

            return call_llm(messages, max_tokens=200)

        except Exception as e:
            print(f"LLM summary generation failed: {e}")
            return f"Workflow completed. Executed {execution_data['successful_nodes']}/{execution_data['total_nodes']} nodes successfully."

    async def run(self, selected_nodes: Optional[list] = None):
        # Start execution timer
        self.execution_start_time = time.time()
        print(f"Starting execution for {self.execution_id}")

        # selected_nodes: if provided, only run that subset (and dependencies)
        to_run = set(self.nodes_by_id.keys()) if not selected_nodes else set(selected_nodes)
        # compute initial ready nodes (no unmet deps)
        ready = [nid for nid in to_run if len(self.deps.get(nid, set())) == 0]
        running_tasks = {}
        print(f"Initial ready nodes: {ready}")

        async def try_schedule(node_id):
            print(f"Trying to schedule {node_id}")
            # ensure dependencies succeeded unless they're independent
            deps = self.deps.get(node_id, set())
            print(f"Dependencies for {node_id}: {deps}")
            for d in deps:
                if self.state[d]['status'] != 'success':
                    # if dependency failed, skip this node (default: stop dependents)
                    print(f"Dependency {d} not successful, skipping {node_id}")
                    self.state[node_id]['status'] = 'skipped'
                    await self._publish({"node": node_id, "status": "skipped", "reason": "dependency_failed"})
                    return
            # schedule
            print(f"Scheduling {node_id}")
            task = asyncio.create_task(self._call_tool(node_id, self.nodes_by_id[node_id]))
            running_tasks[node_id] = task

        # schedule initial
        for nid in ready:
            if nid in to_run:
                await try_schedule(nid)

        # main loop: when a task finishes, check children
        import sys
        print(f"Starting main loop with {len(running_tasks)} running tasks", flush=True)
        while running_tasks:
            print(f"Waiting for task completion, {len(running_tasks)} tasks running", flush=True)
            done, _ = await asyncio.wait(list(running_tasks.values()), return_when=asyncio.FIRST_COMPLETED)
            # find completed nodes and schedule their children
            completed_nodes = []
            for nid, task in list(running_tasks.items()):
                if task.done():
                    print(f"Task {nid} completed", flush=True)
                    completed_nodes.append(nid)
                    running_tasks.pop(nid)

            # schedule children of completed nodes
            print(f"Completed nodes: {completed_nodes}", flush=True)
            for nid in completed_nodes:
                print(f"Checking children of {nid}: {self.children.get(nid, set())}", flush=True)
                for child in self.children.get(nid, set()):
                    if child not in to_run:
                        print(f"Child {child} not in to_run, skipping", flush=True)
                        continue
                    # check if all deps resolved (and not skipped/failed)
                    unmet = [d for d in self.deps.get(child, set()) if self.state[d]['status'] not in ('success')]
                    print(f"Child {child} dependencies check - unmet: {unmet}, status: {self.state[child]['status']}", flush=True)
                    if not unmet and self.state[child]['status'] == 'pending':
                        await try_schedule(child)
            await asyncio.sleep(0.1)
        print("Main loop finished", flush=True)

        # Generate LLM summary of what was accomplished
        print("🔄 Starting LLM summary generation...")
        try:
            llm_summary = await self._generate_execution_summary()
            print(f"✅ LLM summary generated: {llm_summary}")
        except Exception as e:
            print(f"❌ Failed to generate LLM summary: {e}")
            import traceback
            traceback.print_exc()
            llm_summary = "Summary generation failed"

        # After all done, publish final summary with LLM analysis
        final_summary = self.summary()
        final_summary["llm_summary"] = llm_summary
        await self._publish({"type": "finished", "summary": final_summary})
