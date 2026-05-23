# Implementation Notes

`mcp-orchestrator-workbench` is a prototype for exploring how agent workflows can be planned, executed, observed, and deployed across a small service stack.

The repository is intentionally public as a systems artifact: it shows the shape of an agentic application rather than claiming to be a production platform.

## Execution modes

| Mode | Purpose |
|---|---|
| Chat | Natural-language planning with generated execution steps and progress tracking. |
| Agent Flow | Autonomous agent sessions using planner, executor, researcher, and analyst roles. |
| Workflow Builder | Visual composition of tool and agent nodes with execution logging. |

## Service layout

| Area | Path | Role |
|---|---|---|
| Frontend | `frontend/` | React interface for chat, agent flow, and workflow editing. |
| Orchestrator | `orchestrator-service/` | FastAPI service coordinating plans, agents, tools, and logs. |
| Tool server | `mcp-server/` | FastMCP service exposing callable tools. |
| Logging | `logging-service/` | Lightweight execution/event logging service. |
| Infrastructure | `infrastructure/` | Azure Container Apps deployment sketches and scripts. |

## What is implemented

- multi-mode React interface
- FastAPI orchestration API
- basic agent manager and workflow manager
- FastMCP tool-service boundary
- local Docker Compose workflow
- Azure deployment templates
- smoke tests for the Python orchestration layer

## Current verification

Useful local checks:

```bash
cd frontend
npm install
npm run build
```

```bash
python -m unittest discover -s orchestrator-service/tests -v
python -m compileall orchestrator-service logging-service mcp-server
```

## Limits

This is a prototype workbench. Before using it as a production system, the project would need:

- real authentication and authorization review
- secrets handling review
- broader integration tests
- deployment-specific hardening
- clearer persistence and retention rules for logs
- threat modeling around tool execution

The value of the repo is in the architecture and implementation pattern: React UI, FastAPI orchestration, FastMCP tools, logs, local development, and a plausible cloud deployment path in one inspectable codebase.
