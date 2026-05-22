# FastAPI orchestrator: LLM-driven planner + executor + websocket updates
import os
import json
import uuid
import asyncio
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from planner.llm_client import generate_plan_with_llm
from planner.executor import ExecutionManager
from agents.agent_manager import AgentManager
from agents.workflow_manager import WorkflowManager
from utils.mcp_utils import fetch_tools_from_mcp, extract_tool_result
# from fastmcp import Client  # Not needed for direct tool execution

app = FastAPI(title="orchestrator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MCP_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/mcp")
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_CALLS", "4"))

# MCP client removed - using direct tool execution


# In-memory store for executions
EXECUTIONS = {}
AGENT_SESSIONS = {}  # Store for agent-based flow sessions
WORKFLOWS = {}  # Store for workflow-based flow sessions

class PlanRequest(BaseModel):
    goal: str
    hints: dict = None
    chat_history: list = None  # Previous messages and execution results
    model: str = None  # Selected model

@app.get("/tools")
async def get_tools():
    """Get available tools from MCP server via MCP Client"""
    print("[TOOLS] GET /tools endpoint called")

    try:
        print(f"[TOOLS] Connecting to MCP server at {MCP_URL}")
        tools_data = await fetch_tools_from_mcp(MCP_URL)
        print(f"[TOOLS] Successfully fetched {len(tools_data)} tools")
        for tool in tools_data:
            print(f"[TOOLS] - {tool['name']}: {tool['description']}")
        return tools_data

    except Exception as e:
        print(f"[TOOLS] Error fetching tools via MCP Client: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch tools: {str(e)}")

@app.get("/mcp/status")
async def get_mcp_status():
    """Get MCP server connection status and stats"""
    try:
        import time
        start_time = time.time()

        from fastmcp import Client
        async with Client(MCP_URL) as client:
            tools = await client.list_tools()
            tools_count = len(tools)
            response_time = (time.time() - start_time) * 1000  # ms

            return {
                "status": "connected",
                "server_url": MCP_URL,
                "tools_count": tools_count,
                "response_time_ms": round(response_time, 2),
                "timestamp": time.time()
            }
    except Exception as e:
        return {
            "status": "disconnected",
            "server_url": MCP_URL,
            "error": str(e),
            "timestamp": time.time()
        }




@app.post("/plan")
async def plan(req: PlanRequest):
    # Use hardcoded tools for planning
    tool_meta = await get_tools()

    # Always use LLM for planning - no pattern matching
    try:
        raw = generate_plan_with_llm(tool_meta, req.goal, req.chat_history)
        plan = None
        if isinstance(raw, dict) and "plan" in raw:
            plan = raw["plan"]
        else:
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    plan = parsed.get("plan", parsed)
                except Exception:
                    pass

        if not plan:
            # If LLM fails, return error instead of fallback
            raise HTTPException(status_code=500, detail="Failed to generate plan with LLM")

        # Basic validation
        tool_names = {t["name"] for t in tool_meta}
        nodes = plan.get("nodes", [])
        for n in nodes:
            if n.get("tool") not in tool_names:
                print(f"Warning: Plan uses unknown tool {n.get('tool')}")

        return {"plan": plan, "llm_raw": raw}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in planning: {e}")
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")

@app.post("/execute")
async def execute(payload: dict):
    plan = payload.get("plan")
    selected = payload.get("selected_nodes")
    if not plan:
        raise HTTPException(status_code=400, detail="Missing plan")
    execution_id = str(uuid.uuid4())
    manager = ExecutionManager(execution_id, plan, MCP_URL, max_concurrency=MAX_CONCURRENT)
    EXECUTIONS[execution_id] = manager

    # start execution in background
    async def run_with_error_handling():
        try:
            await manager.run(selected_nodes=selected)
        except Exception as e:
            print(f"Error in background execution: {e}")
            import traceback
            traceback.print_exc()

    asyncio.create_task(run_with_error_handling())
    return {"execution_id": execution_id}

@app.get("/execution/{eid}")
async def get_execution(eid: str):
    manager = EXECUTIONS.get(eid)
    if not manager:
        raise HTTPException(status_code=404, detail="Execution not found")
    return manager.summary()

# Websocket endpoint for real-time updates
@app.websocket("/ws/execution/{eid}")
async def websocket_exec(websocket: WebSocket, eid: str):
    await websocket.accept()
    manager = EXECUTIONS.get(eid)
    if not manager:
        await websocket.send_json({"error": "execution not found"})
        await websocket.close()
        return
    sub = manager.subscribe()
    try:
        while True:
            update = await sub.get()
            await websocket.send_json(update)
    except WebSocketDisconnect:
        # client disconnected
        pass

@app.get("/test/tools-list")
async def test_tools_list():
    """Test 1: Can we list tools from MCP server?"""
    print("\n" + "="*80)
    print("[TEST-TOOLS-LIST] Starting tool listing test")
    print("="*80)

    try:
        start_time = time.time()
        print(f"[TEST-TOOLS-LIST] Connecting to MCP server at {MCP_URL}")

        tools = await get_tools()
        elapsed = time.time() - start_time

        print(f"[TEST-TOOLS-LIST] ✅ Success! Retrieved {len(tools)} tools in {elapsed:.2f}s")
        print("="*80 + "\n")

        return {
            "test": "tools_list",
            "status": "success",
            "elapsed_seconds": elapsed,
            "tools_count": len(tools),
            "tools": tools
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[TEST-TOOLS-LIST] ❌ Failed after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        return {
            "test": "tools_list",
            "status": "error",
            "elapsed_seconds": elapsed,
            "error": str(e)
        }

@app.get("/test/tool-call")
async def test_tool_call():
    """Test 2: Can we call a simple tool directly?"""
    print("\n" + "="*80)
    print("[TEST-TOOL-CALL] Starting direct tool call test")
    print("="*80)

    try:
        start_time = time.time()
        print(f"[TEST-TOOL-CALL] Connecting to MCP server at {MCP_URL}")

        from fastmcp import Client
        async with Client(MCP_URL) as client:
            connect_time = time.time() - start_time
            print(f"[TEST-TOOL-CALL] Connected in {connect_time:.2f}s")
            print("[TEST-TOOL-CALL] Calling echo tool with 'test message'")

            call_start = time.time()
            result = await client.call_tool("echo", {"text": "test message"})
            call_time = time.time() - call_start

            print(f"[TEST-TOOL-CALL] Tool call completed in {call_time:.2f}s")
            print(f"[TEST-TOOL-CALL] Result: {result}")

            # Extract result
            if hasattr(result, 'content') and result.content:
                if isinstance(result.content, list) and len(result.content) > 0:
                    output = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                else:
                    output = str(result.content)
            else:
                output = str(result)

            elapsed = time.time() - start_time
            print(f"[TEST-TOOL-CALL] ✅ Success! Total time: {elapsed:.2f}s")
            print("="*80 + "\n")

            return {
                "test": "tool_call",
                "status": "success",
                "elapsed_seconds": elapsed,
                "connect_time": connect_time,
                "call_time": call_time,
                "tool": "echo",
                "input": {"text": "test message"},
                "output": output
            }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[TEST-TOOL-CALL] ❌ Failed after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        return {
            "test": "tool_call",
            "status": "error",
            "elapsed_seconds": elapsed,
            "error": str(e)
        }

@app.get("/test/all")
async def test_all():
    """Run all tests in sequence"""
    print("\n" + "="*80)
    print("[TEST-ALL] Starting comprehensive test suite")
    print("="*80 + "\n")

    results = {}

    # Test 1: List tools
    print("[TEST-ALL] Running Test 1: List Tools")
    results["test1_tools_list"] = await test_tools_list()

    # Test 2: Call a tool
    print("[TEST-ALL] Running Test 2: Direct Tool Call")
    results["test2_tool_call"] = await test_tool_call()

    # Summary
    all_passed = all(r.get("status") == "success" for r in results.values())

    print("\n" + "="*80)
    print("[TEST-ALL] Test Suite Complete")
    print(f"[TEST-ALL] Status: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    for test_name, result in results.items():
        status_icon = "✅" if result.get("status") == "success" else "❌"
        print(f"[TEST-ALL]   {status_icon} {test_name}: {result.get('status')}")
    print("="*80 + "\n")

    return {
        "test_suite": "comprehensive",
        "overall_status": "success" if all_passed else "failure",
        "results": results
    }

@app.post("/chat")
async def chat(req: PlanRequest):
    """Simple chatbot - just responds to user messages"""
    print('[CHAT] Starting chat request')
    from planner.llm_client import call_llm

    # Build conversation messages
    messages = [
        {"role": "system", "content": "You are a helpful, friendly AI assistant. Respond to the user's questions and engage in natural conversation. Be concise but informative."}
    ]

    # Add chat history for context (last 10 messages for better conversation flow)
    if req.chat_history:
        for entry in req.chat_history[-10:]:
            if entry.get("type") == "user":
                messages.append({"role": "user", "content": entry.get("content", "")})
            elif entry.get("type") == "assistant":
                messages.append({"role": "assistant", "content": entry.get("content", "")})

    # Add current user message
    messages.append({"role": "user", "content": req.goal})

    try:
        content = call_llm(messages, max_tokens=500)
        print('[CHAT] Successfully received LLM response')

        return {
            "type": "chat",
            "content": content,
            "model_used": req.model or "default"
        }

    except RuntimeError as e:
        # Handle token/API errors specifically
        error_msg = str(e)
        print(f"[CHAT ERROR] Runtime error: {error_msg}")

        # Return user-friendly error message
        if "token" in error_msg.lower() or "rate limit" in error_msg.lower():
            return JSONResponse(
                status_code=503,
                content={
                    "type": "chat",
                    "content": f"⚠️ API Error: {error_msg}",
                    "error": error_msg
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "type": "chat",
                    "content": "I'm experiencing technical difficulties. Please try again.",
                    "error": error_msg
                }
            )

    except Exception as e:
        print(f"[CHAT ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "type": "chat",
                "content": "I'm experiencing technical difficulties. Please try again.",
                "error": str(e)
            }
        )

# ============= AGENT-BASED FLOW ENDPOINTS =============

@app.post("/agent-flow/start")
async def start_agent_flow(payload: dict):
    """
    Start an agent-based flow where agents work autonomously.
    Payload: {
        "agent_type": "planner" | "executor" | "researcher" | "analyst",
        "goal": "what the agent should accomplish",
        "context": {} (optional),
        "selected_tools": [] (optional - list of tool names to use)
    }
    """
    agent_type = payload.get("agent_type", "executor")
    goal = payload.get("goal", "")
    context = payload.get("context", {})
    selected_tools = payload.get("selected_tools", None)

    if not goal:
        raise HTTPException(status_code=400, detail="Goal is required")

    session_id = str(uuid.uuid4())
    manager = AgentManager(session_id, MCP_URL)
    AGENT_SESSIONS[session_id] = manager

    # Start AgentFlow in background
    async def run_agent():
        try:
            await manager.run_agent_flow(agent_type, goal, context, selected_tools)
        except Exception as e:
            print(f"Error in AgentFlow: {e}")
            import traceback
            traceback.print_exc()

    asyncio.create_task(run_agent())

    return {"session_id": session_id, "agent_type": agent_type, "goal": goal, "selected_tools": selected_tools}

@app.get("/agent-flow/{session_id}")
async def get_agent_flow_status(session_id: str):
    """Get the current status of an AgentFlow"""
    manager = AGENT_SESSIONS.get(session_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Session not found")
    return manager.get_summary()

@app.websocket("/ws/agent-flow/{session_id}")
async def websocket_agent_flow(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time AgentFlow updates"""
    await websocket.accept()
    manager = AGENT_SESSIONS.get(session_id)
    if not manager:
        await websocket.send_json({"error": "session not found"})
        await websocket.close()
        return

    sub = manager.subscribe()
    try:
        while True:
            update = await sub.get()
            await websocket.send_json(update)
            # Close connection when flow completes
            if update.get("type") in ["flow_complete", "flow_error"]:
                break
    except WebSocketDisconnect:
        pass

# ============= WORKFLOW-BASED FLOW ENDPOINTS =============

@app.post("/workflow/create")
async def create_workflow(payload: dict):
    """
    Create a new workflow.
    Payload: {
        "nodes": [
            {"id": "n1", "type": "tool", "config": {"tool": "echo", "params": {"message": "hello"}}},
            {"id": "n2", "type": "agent", "config": {"agent_type": "executor", "goal": "do something"}}
        ],
        "edges": [{"from": "n1", "to": "n2"}]
    }
    """
    workflow_id = str(uuid.uuid4())
    manager = WorkflowManager(workflow_id, MCP_URL)

    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])

    # Add nodes
    for node in nodes:
        manager.add_node(node["id"], node["type"], node.get("config", {}))

    # Add edges
    for edge in edges:
        manager.add_edge(edge["from"], edge["to"])

    WORKFLOWS[workflow_id] = manager

    return {"workflow_id": workflow_id, "nodes": len(nodes), "edges": len(edges)}

@app.post("/workflow/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):
    """Execute a workflow"""
    manager = WORKFLOWS.get(workflow_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Start execution in background
    async def run_workflow():
        try:
            await manager.execute()
        except Exception as e:
            print(f"Error in workflow execution: {e}")
            import traceback
            traceback.print_exc()

    asyncio.create_task(run_workflow())

    return {"workflow_id": workflow_id, "status": "started"}

@app.get("/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    manager = WORKFLOWS.get(workflow_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return manager.get_summary()

@app.post("/workflow/{workflow_id}/save")
async def save_workflow(workflow_id: str, payload: dict = Body(None)):
    """Export workflow as JSON - either from memory or from provided data"""
    print(f"[WORKFLOW SAVE] workflow_id={workflow_id}, payload type={type(payload)}, payload={payload}")

    # Try to get from WORKFLOWS first
    manager = WORKFLOWS.get(workflow_id)

    if manager:
        # Export from existing workflow manager
        workflow_json = manager.to_dict()
        print(f"[WORKFLOW] Exported workflow {workflow_id} from memory: {len(workflow_json['nodes'])} nodes, {len(workflow_json['edges'])} edges")
    elif payload and payload.get("workflow"):
        # Use provided workflow data
        workflow_json = payload.get("workflow")
        print(f"[WORKFLOW] Exported workflow {workflow_id} from provided data: {len(workflow_json.get('nodes', []))} nodes, {len(workflow_json.get('edges', []))} edges")
    else:
        print(f"[WORKFLOW SAVE ERROR] manager={manager}, payload={payload}")
        raise HTTPException(status_code=404, detail="Workflow not found and no data provided")

    return {
        "status": "success",
        "workflow": workflow_json
    }

@app.post("/workflow/load")
async def load_workflow(payload: dict):
    """Import workflow from JSON"""
    try:
        from agents.workflow_manager import WorkflowManager

        workflow_data = payload.get("workflow")
        if not workflow_data:
            raise HTTPException(status_code=400, detail="Missing workflow data")

        # Create workflow manager from JSON
        manager = WorkflowManager.from_dict(workflow_data, MCP_URL)

        # Store in WORKFLOWS
        WORKFLOWS[manager.workflow_id] = manager

        print(f"[WORKFLOW] Loaded workflow {manager.workflow_id}")

        return {
            "status": "success",
            "workflow_id": manager.workflow_id,
            "nodes": len(manager.nodes),
            "edges": len(manager.edges)
        }

    except Exception as e:
        print(f"[WORKFLOW] Error loading workflow: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to load workflow: {str(e)}")

@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_workflow(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates"""
    await websocket.accept()
    manager = WORKFLOWS.get(workflow_id)
    if not manager:
        await websocket.send_json({"error": "workflow not found"})
        await websocket.close()
        return

    sub = manager.subscribe()
    try:
        while True:
            update = await sub.get()
            await websocket.send_json(update)
            # Close connection when workflow completes
            if update.get("type") in ["workflow_complete", "workflow_error"]:
                break
    except WebSocketDisconnect:
        pass

# ============= DSPY OPTIMIZATION ENDPOINTS =============

@app.post("/dspy/optimize")
async def optimize_with_dspy(payload: dict):
    """
    Optimize MCP prompts using DSPy with training examples.
    Payload: {
        "optimization_type": "param_enhance" | "param_recovery" | "plan_gen" | "tool_select",
        "training_examples": [...],
        "validation_examples": [...] (optional)
    }
    """
    try:
        from utils.dspy_optimizer import get_optimizer

        optimization_type = payload.get("optimization_type")
        training_examples = payload.get("training_examples", [])
        validation_examples = payload.get("validation_examples")

        if not optimization_type or not training_examples:
            raise HTTPException(status_code=400, detail="optimization_type and training_examples are required")

        # Get optimizer and run optimization
        optimizer = get_optimizer()
        result = await optimizer.optimize_with_examples(
            optimization_type,
            training_examples,
            validation_examples
        )

        return result

    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        print(f"[DSPY] Optimization error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/dspy/status")
async def get_dspy_status():
    """Get DSPy optimization status and verify LLM availability"""
    try:
        from utils.dspy_optimizer import get_optimizer
        import requests

        optimizer = get_optimizer()
        status_data = optimizer.get_optimization_status()

        # Test actual LLM availability with a minimal call
        llm_status = "ready"
        llm_error = None

        try:
            # Make a minimal test call to verify LLM is working
            if optimizer.llm_provider == "github":
                endpoint = "https://models.inference.ai.azure.com/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {optimizer.lm.token}"
                }

                # Minimal test payload
                test_payload = {
                    "model": optimizer.lm.model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                }

                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=test_payload,
                    timeout=10
                )

                # Check for rate limiting
                if response.status_code == 429:
                    llm_status = "rate_limited"
                    llm_error = "GitHub API rate limit exceeded. Please wait before making more requests."
                elif not response.ok:
                    llm_status = "error"
                    try:
                        error_data = response.json()
                        llm_error = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
                    except:
                        llm_error = f"HTTP error {response.status_code}"

        except requests.exceptions.Timeout:
            llm_status = "timeout"
            llm_error = "LLM request timed out"
        except requests.exceptions.ConnectionError:
            llm_status = "connection_error"
            llm_error = "Could not connect to LLM service"
        except Exception as test_error:
            llm_status = "error"
            llm_error = str(test_error)
            print(f"[DSPY] LLM test call failed: {test_error}")

        response_data = {
            "status": llm_status,
            "llm_provider": optimizer.llm_provider,
            "optimizations": status_data,
            "available_types": ["param_enhance", "param_recovery", "plan_gen", "tool_select"]
        }

        if llm_error:
            response_data["error"] = llm_error

        return response_data

    except Exception as e:
        print(f"[DSPY] Status error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "llm_provider": "unknown"
        }

@app.post("/dspy/optimize-auto")
async def auto_optimize(payload: dict):
    """
    Auto-generate training examples from execution logs and optimize.
    Payload: {
        "optimization_type": "param_enhance" | "param_recovery" | "plan_gen",
        "execution_ids": [] (optional - use recent executions if not provided),
        "agent_session_ids": [] (optional - use agent sessions for param recovery examples)
    }
    """
    try:
        from utils.dspy_optimizer import get_optimizer

        optimization_type = payload.get("optimization_type")
        execution_ids = payload.get("execution_ids", [])
        agent_session_ids = payload.get("agent_session_ids", [])

        if not optimization_type:
            raise HTTPException(status_code=400, detail="optimization_type is required")

        training_examples = []

        # Generate examples based on optimization type
        if optimization_type == "param_enhance":
            # Extract from execution logs
            for eid in execution_ids:
                manager = EXECUTIONS.get(eid)
                if manager:
                    for node_id, state in manager.state.items():
                        node = manager.nodes_by_id.get(node_id)
                        if node and state.get("status") == "success":
                            # Create training example from successful execution
                            training_examples.append({
                                "tool_name": node["tool"],
                                "tool_schema": node.get("params_template", {}),
                                "current_params": node.get("params_template", {}),
                                "execution_context": [],
                                "expected_params": node.get("params_template", {})
                            })

        elif optimization_type == "param_recovery":
            # Extract from agent sessions that had errors
            for session_id in agent_session_ids:
                manager = AGENT_SESSIONS.get(session_id)
                if manager:
                    for log_entry in manager.execution_log:
                        if log_entry.get("type") == "tool_call_retry":
                            training_examples.append({
                                "tool_name": log_entry["tool"],
                                "tool_schema": {},  # Would need to fetch from MCP
                                "failed_params": log_entry["previous_params"],
                                "error_message": log_entry["error"],
                                "expected_params": log_entry["corrected_params"]
                            })

        elif optimization_type == "plan_gen":
            # Extract from successful executions
            for eid in execution_ids:
                manager = EXECUTIONS.get(eid)
                if manager and manager.plan:
                    # Would need the original goal to create proper training example
                    # This is a simplified version
                    training_examples.append({
                        "user_goal": "extracted from execution",
                        "available_tools": await get_tools(),
                        "tool_schemas": {},
                        "chat_history": [],
                        "expected_plan": manager.plan
                    })

        if not training_examples:
            return {
                "status": "no_examples",
                "message": "No training examples could be generated from provided execution logs",
                "training_examples_count": 0
            }

        # Run optimization
        optimizer = get_optimizer()
        result = await optimizer.optimize_with_examples(
            optimization_type,
            training_examples
        )

        result["auto_generated_examples"] = len(training_examples)
        return result

    except Exception as e:
        print(f"[DSPY] Auto-optimization error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auto-optimization failed: {str(e)}")

@app.get("/dspy/test")
async def test_dspy():
    """Test DSPy integration with a simple example"""
    try:
        from utils.dspy_optimizer import get_optimizer

        optimizer = get_optimizer()

        # Test parameter enhancement
        result = await optimizer.enhance_parameters(
            tool_name="echo",
            tool_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
            current_params={"message": "hello"},
            execution_context=[]
        )

        return {
            "status": "success",
            "test_type": "param_enhance",
            "input_params": {"message": "hello"},
            "output_params": result,
            "message": "DSPy is working correctly"
        }

    except Exception as e:
        print(f"[DSPY] Test error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/dspy/optimize-from-feedback")
async def optimize_from_feedback():
    """
    Optimize MCP configs based on collected user feedback.
    Analyzes patterns and updates YAML configs.
    """
    try:
        print("[DSPY] Starting feedback-based config optimization...")
        from utils.feedback_analyzer import get_feedback_analyzer

        # Use the feedback analyzer to update configs
        analyzer = get_feedback_analyzer()
        result = await analyzer.analyze_and_update_configs()

        return result

    except Exception as e:
        print(f"[DSPY] Feedback optimization error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/dspy/feedback/stats")
async def get_feedback_stats():
    """Get statistics about collected feedback"""
    try:
        import requests
        logging_url = os.getenv("LOGGING_SERVICE_URL", "http://logging-service:8200")

        # Get user feedback count
        feedback_response = requests.get(
            f"{logging_url}/logs/llm",
            params={"limit": 1000},
            timeout=10
        )

        if feedback_response.ok:
            feedback_data = feedback_response.json()
            total_logs = feedback_data.get("total", 0)
            logs = feedback_data.get("logs", [])

            # Count by service
            by_service = {}
            for log in logs:
                service = log.get("service", "unknown")
                by_service[service] = by_service.get(service, 0) + 1

            return {
                "status": "success",
                "total_examples": total_logs,
                "available_examples": len(logs),
                "by_service": by_service,
                "ready_to_optimize": total_logs >= 5
            }
        else:
            return {
                "status": "error",
                "error": "Failed to fetch feedback statistics"
            }

    except Exception as e:
        print(f"[DSPY] Failed to get feedback stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/dspy/feedback")
async def submit_feedback(payload: dict):
    """
    Submit user feedback to improve DSPy optimizations.
    Payload: {
        "feedback_type": "tool_call" | "parameter_correction" | "workflow",
        "rating": "positive" | "negative" | "correction",
        "data": {
            "tool_name": "...",
            "wrong_params": {...},
            "correct_params": {...},
            ...
        }
    }
    """
    try:
        from utils.dspy_optimizer import get_optimizer

        feedback_type = payload.get("feedback_type")
        rating = payload.get("rating")
        data = payload.get("data", {})

        if not feedback_type or not rating:
            raise HTTPException(status_code=400, detail="feedback_type and rating are required")

        optimizer = get_optimizer()
        success = await optimizer.record_user_feedback(feedback_type, data, rating)

        # Also send to centralized logging service
        try:
            import requests
            logging_url = os.getenv("LOGGING_SERVICE_URL", "http://logging-service:8200")
            requests.post(
                f"{logging_url}/logs/feedback",
                json={
                    "feedback_type": feedback_type,
                    "rating": rating,
                    "session_id": data.get("session_id"),
                    "data": data,
                    "user_query": data.get("user_query"),
                    "tool_calls": data.get("tool_calls"),
                    "execution_data": data.get("execution_data")
                },
                timeout=2
            )
        except Exception as log_error:
            print(f"[Feedback] Warning: Failed to send to logging service: {log_error}")

        return {
            "status": "success" if success else "error",
            "message": "Feedback recorded successfully" if success else "Failed to record feedback"
        }

    except Exception as e:
        print(f"[DSPY Feedback] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

# ============= MCP OPERATIONALIZATION ENDPOINTS =============

@app.post("/mcp/test-suite/generate")
async def generate_test_suite(count: int = 5):
    """
    Generate LLM-driven test suite for all MCP tools.
    Creates test cases with task + expected output.
    """
    try:
        from utils.test_suite_manager import get_test_manager

        # Get available tools
        tools = await get_tools()

        test_manager = get_test_manager()
        test_cases = await test_manager.generate_test_cases(tools, count=count)

        return {
            "status": "success",
            "test_count": len(test_cases),
            "suite_id": f"suite_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "message": f"Generated {len(test_cases)} test cases",
            "preview": test_cases[:3]  # Show first 3
        }

    except Exception as e:
        print(f"[TestGen] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/mcp/test-suite/{suite_id}/run")
async def run_test_suite(suite_id: str):
    """
    Run a test suite through AgentFlow.
    Validates actual vs expected outputs.
    """
    try:
        from utils.test_suite_manager import get_test_manager

        test_manager = get_test_manager()
        results = await test_manager.run_test_suite(suite_id)

        return results

    except Exception as e:
        print(f"[TestRun] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/mcp/test-suites")
async def list_test_suites():
    """List all available test suites"""
    try:
        from utils.test_suite_manager import get_test_manager

        test_manager = get_test_manager()
        suites = test_manager.get_test_suites()

        return {
            "status": "success",
            "suites": suites,
            "count": len(suites)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/mcp/test-suite/{suite_id}/results")
async def get_test_results(suite_id: str):
    """Get results for a specific test suite"""
    try:
        from utils.test_suite_manager import get_test_manager

        test_manager = get_test_manager()
        results = test_manager.get_test_results(suite_id)

        if results:
            return results
        else:
            raise HTTPException(status_code=404, detail="Results not found")

    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/mcp/configs/optimize")
async def optimize_configs_from_feedback():
    """
    Analyze user feedback and update MCP tool configs.
    This is the main operationalization endpoint.
    """
    try:
        from utils.feedback_analyzer import get_feedback_analyzer

        analyzer = get_feedback_analyzer()
        result = await analyzer.analyze_and_update_configs()

        return result

    except Exception as e:
        print(f"[ConfigOptimize] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/dspy/status/enhanced")
async def get_enhanced_dspy_status():
    """Get enhanced DSPy status with YAML configs, feedback, and detailed metrics"""
    try:
        from utils.dspy_optimizer import get_optimizer

        optimizer = get_optimizer()

        # Get basic status
        basic_status = optimizer.get_optimization_status()

        # Get YAML config summary
        yaml_summary = optimizer.get_yaml_config_summary()

        # Get feedback summary
        feedback_summary = optimizer.get_feedback_summary()

        return {
            "status": "ready",
            "llm_provider": optimizer.llm_provider,
            "optimizations": basic_status,
            "yaml_configs": yaml_summary,
            "user_feedback": feedback_summary,
            "available_types": ["param_enhance", "param_recovery", "plan_gen", "tool_select"]
        }

    except Exception as e:
        print(f"[DSPY] Enhanced status error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/dspy/configs/{tool_name}")
async def get_tool_config(tool_name: str):
    """Get YAML configuration for a specific tool"""
    try:
        from utils.config_manager import get_config_manager

        config_manager = get_config_manager()
        config = config_manager.load_tool_config(tool_name)

        if config:
            return {
                "status": "success",
                "tool_name": tool_name,
                "config": config
            }
        else:
            return {
                "status": "not_found",
                "tool_name": tool_name,
                "message": f"No configuration found for {tool_name}"
            }

    except Exception as e:
        print(f"[Config] Error getting tool config: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/dspy/orchestrator-config")
async def get_orchestrator_config():
    """Export orchestrator configuration including all optimization metrics"""
    try:
        from utils.config_manager import get_config_manager
        from utils.dspy_optimizer import get_optimizer

        config_manager = get_config_manager()
        optimizer = get_optimizer()

        # Get orchestrator config
        orch_config = config_manager.load_orchestrator_config()

        # Add current optimization status
        opt_status = optimizer.get_optimization_status()

        # Combine everything
        export_data = {
            **orch_config,
            "current_optimizations": opt_status,
            "export_timestamp": __import__('datetime').datetime.now().isoformat(),
            "version": "1.0"
        }

        return {
            "status": "success",
            "config": export_data
        }

    except Exception as e:
        print(f"[Config] Error getting orchestrator config: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/dspy/training-examples")
async def get_training_examples():
    """Get real examples from the last training run"""
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()

        # Load all tool configs to get their examples
        all_examples = {}

        # Get list of tools
        try:
            mcp_client = Client(MCP_URL)
            async with mcp_client:
                tools_result = await mcp_client.list_tools()
                tool_names = [t.name for t in tools_result]
        except Exception as e:
            print(f"Error fetching tools: {e}")
            tool_names = []

        # Load examples for each tool
        for tool_name in tool_names:
            try:
                config = config_manager.load_tool_config(tool_name)
                if config and config.get('examples'):
                    all_examples[tool_name] = config['examples']
            except Exception as e:
                print(f"Error loading config for {tool_name}: {e}")

        return {
            "status": "success",
            "examples": all_examples,
            "total_tools": len(tool_names),
            "tools_with_examples": len(all_examples)
        }

    except Exception as e:
        print(f"[Training Examples] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/dspy/call-logs")
async def get_call_logs():
    """Get detailed call logs for all tools"""
    try:
        from utils.config_manager import get_config_manager
        from utils.dspy_optimizer import get_optimizer

        config_manager = get_config_manager()
        optimizer = get_optimizer()

        # Get list of tools
        try:
            mcp_client = Client(MCP_URL)
            async with mcp_client:
                tools_result = await mcp_client.list_tools()
                tool_names = [t.name for t in tools_result]
        except Exception as e:
            print(f"Error fetching tools: {e}")
            tool_names = []

        # Collect detailed logs for each tool
        detailed_logs = {}

        for tool_name in tool_names:
            try:
                config = config_manager.load_tool_config(tool_name)
                if not config:
                    continue

                tool_log = {
                    "tool_name": tool_name,
                    "description": config.get('tool', {}).get('description', ''),
                    "successful_calls": [],
                    "failed_calls": [],
                    "corrections": [],
                    "metrics": config.get('optimization', {}).get('accuracy_metrics', {})
                }

                # Extract successful calls from examples
                examples = config.get('examples', [])
                for example in examples:
                    tool_log["successful_calls"].append({
                        "description": example.get('description', ''),
                        "input": example.get('input', {}),
                        "expected_output": example.get('expected_output', {}),
                        "timestamp": example.get('timestamp', None)
                    })

                # Extract corrections from learned patterns
                learned_patterns = config.get('optimization', {}).get('learned_patterns', [])
                for pattern in learned_patterns:
                    if pattern.get('type') == 'correction':
                        tool_log["corrections"].append({
                            "parameter": pattern.get('parameter', ''),
                            "before": pattern.get('before', ''),
                            "after": pattern.get('after', ''),
                            "frequency": pattern.get('frequency', 1),
                            "reason": pattern.get('reason', '')
                        })

                # Add parameter mappings as corrections
                name_mappings = config.get('parameters', {}).get('name_mappings', {})
                for wrong_name, correct_name in name_mappings.items():
                    tool_log["corrections"].append({
                        "parameter": correct_name,
                        "before": f"{wrong_name} (incorrect)",
                        "after": f"{correct_name} (correct)",
                        "frequency": "common",
                        "reason": "Parameter name mapping"
                    })

                detailed_logs[tool_name] = tool_log

            except Exception as e:
                print(f"Error loading logs for {tool_name}: {e}")

        return {
            "status": "success",
            "logs": detailed_logs,
            "total_tools": len(tool_names)
        }

    except Exception as e:
        print(f"[Call Logs] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/dspy/generate-examples")
async def generate_examples():
    """Generate example prompts using LLM based on available tools"""
    try:
        # Get list of available tools
        mcp_client = Client(MCP_URL)
        async with mcp_client:
            tools_result = await mcp_client.list_tools()

            # Build tool descriptions
            tool_list = []
            for tool in tools_result:
                tool_list.append({
                    "name": tool.name,
                    "description": tool.description if hasattr(tool, 'description') else "No description"
                })

        # Create prompt for LLM
        prompt = f"""You are helping generate example user prompts for an AI agent system.

Available Tools:
{json.dumps(tool_list, indent=2)}

Generate 5 diverse example prompts that users might ask, where the agent would use these tools to help them.

Requirements:
- Make prompts realistic and practical
- Cover different tool combinations
- Range from simple (1 tool) to complex (multiple tools)
- Focus on real-world use cases
- Make them conversational and natural

Return ONLY a JSON array of prompt strings:
["prompt 1", "prompt 2", "prompt 3", "prompt 4", "prompt 5"]"""

        messages = [
            {"role": "system", "content": "You are an expert at understanding tool capabilities and generating realistic user queries. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        # Call LLM
        from planner.llm_client import call_llm
        response = call_llm(messages, max_tokens=500)

        # Parse response
        examples = json.loads(response)

        return {
            "status": "success",
            "examples": examples,
            "tools_analyzed": len(tool_list)
        }

    except Exception as e:
        print(f"[Generate Examples] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "examples": [
                "What's the weather in New York?",
                "Translate 'hello world' to Spanish",
                "Generate a random number between 1 and 100"
            ]
        }
