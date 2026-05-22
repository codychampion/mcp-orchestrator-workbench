# Architecture

MCP Orchestrator Workbench is a prototype for inspecting and executing AI-agent workflows across a browser UI, an orchestration API, a FastMCP tool layer, and an execution log service.

The goal is not to hide agent behavior behind a chat box. The goal is to make plans, tool calls, workflow state, and execution traces visible enough that a developer can reason about what the system is doing.

## Problem

Agentic systems are easiest to demo when everything is a single chat loop. They become harder to trust when they need to coordinate tools, agents, retries, logs, configuration, deployment, and user-facing state.

This workbench explores that middle layer:

- how a user request becomes a plan
- how a plan becomes executable workflow state
- how tool calls are routed through an MCP server
- how agent roles can act over shared context
- how execution status and logs become inspectable UI state

## System Shape

```text
React frontend
  -> FastAPI orchestrator
     -> planner and workflow manager
     -> agent manager
     -> LLM provider layer
     -> FastMCP tool server
     -> logging service
```

The frontend provides three interaction modes:

| Mode | Purpose |
|---|---|
| Chat Mode | Natural-language planning and execution with generated plan state |
| Agent Flow | Autonomous agent execution with planner, executor, researcher, and analyst roles |
| Workflow Builder | Visual workflow construction with connected tool and agent nodes |

The backend keeps those modes tied to the same core concepts: plans, nodes, edges, tool calls, status updates, and execution logs.

## Components

| Component | Responsibility |
|---|---|
| `frontend/` | React UI for chat, agent flow, workflow building, tool viewing, and optimizer surfaces |
| `orchestrator-service/` | FastAPI service that coordinates planning, workflow execution, agents, tools, and provider configuration |
| `mcp-server/` | FastMCP server exposing callable tools through YAML-backed configuration and Python implementations |
| `logging-service/` | Lightweight log capture and admin inspection surface |
| `infrastructure/` | Azure Container Apps deployment sketch with auth and environment wiring |

## Execution Flow

1. A user starts in chat, agent flow, or workflow builder mode.
2. The frontend sends the request or workflow graph to the orchestrator.
3. The orchestrator builds or loads plan state and assigns work to agents or tool nodes.
4. Tool requests are routed to the FastMCP server.
5. Results are normalized into text or structured summaries for downstream steps.
6. Logs and status updates are captured for UI inspection.
7. The frontend renders progress, outputs, and workflow state.

## Design Choices

**Mock-first development.** The repo supports mock mode so the system shape can be tested without live model credentials.

**Tool boundary through MCP.** Tools live behind a FastMCP server rather than being embedded directly in the frontend or orchestrator. This keeps tool definitions, routing, and execution behavior easier to inspect.

**Visible workflow state.** The workbench treats workflow nodes, edges, and statuses as first-class artifacts instead of transient implementation details.

**Small services over one monolith.** The frontend, orchestrator, MCP server, and logging service are separated so each piece has a clear boundary and can be deployed or replaced independently.

**Deployment path included, not overclaimed.** Azure Container Apps files are included as a prototype deployment path. They are examples to adapt, not a claim of production readiness.

## Verification

The public repo keeps a fast smoke workflow:

- frontend dependency install and production build
- Python service compile check
- orchestration unit tests

Local checks:

```bash
cd frontend
npm install
npm run build
```

```bash
python -m compileall orchestrator-service mcp-server logging-service
python -m unittest discover -s orchestrator-service/tests -v
```

## Current Limits

This is a prototype workbench, not a hardened production agent platform.

Known limits:

- authentication and authorization are deployment-specific
- live provider behavior depends on external model credentials
- workflow execution is designed for inspection and experimentation rather than high-throughput production use
- deployment templates need environment-specific review before use

## Why This Matters

For AI engineering work, the interesting part is often not "can an agent call a tool?" It is whether the system around that agent makes behavior inspectable, repeatable, configurable, and safe enough to improve.

This repo is a compact demonstration of that systems layer: frontend experience, orchestration logic, MCP tools, local development, deployment scaffolding, and verification in one coherent workbench.
