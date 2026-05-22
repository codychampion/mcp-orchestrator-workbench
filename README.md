# MCP Orchestrator Workbench

![Status](https://img.shields.io/badge/status-prototype-f59e0b)
![MCP](https://img.shields.io/badge/MCP-FastMCP-7c3aed)
![Backend](https://img.shields.io/badge/backend-FastAPI-059669)
![Frontend](https://img.shields.io/badge/frontend-React-61dafb)
![Deployment](https://img.shields.io/badge/deploy-Azure%20Container%20Apps-2563eb)

A prototype workbench for planning, visualizing, and executing AI-agent workflows across chat, autonomous agent flow, and visual workflow modes.

It shows a complete agentic-system shape: a React frontend, FastAPI orchestrator, FastMCP tool server, logging service, local Docker Compose workflow, and Azure deployment path.

## What it demonstrates

| Area | What it shows |
|---|---|
| Agent orchestration | Chat planning, autonomous agent flow, and visual workflow execution |
| Frontend | React UI for chat, agent execution, and workflow building |
| Backend | FastAPI orchestrator coordinating plans, tools, agents, and logs |
| Tool layer | FastMCP server exposing callable tools |
| Observability | Logging service and execution tracking patterns |
| Deployment | Docker Compose locally, Azure Container Apps for cloud deployment |

## Execution modes

### Chat Mode
Natural-language planning and execution with generated plans, DAG-style visualization, and progress tracking.

### Agent Flow
Autonomous agent execution with planner, executor, researcher, and analyst roles.

### Workflow Builder
Visual workflow creation with connected tools and agents.

## Architecture

For the deeper system walkthrough, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

```text
React frontend
  -> FastAPI orchestrator
     -> FastMCP tool server
     -> logging service
     -> LLM provider layer
```

Optional deployment path:

```text
Azure Container Apps + Azure AD auth + Key Vault + Container Registry + App Insights
```

## Quick start

Use mock mode for local development without model credentials:

```bash
git clone https://github.com/codychampion/mcp-orchestrator-workbench.git
cd mcp-orchestrator-workbench
export LLM_PROVIDER=mock
docker compose up -d
```

Local services:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Orchestrator API | http://localhost:8100 |
| MCP server | http://localhost:8000 |
| Logging service | http://localhost:8200 |

To use GitHub Models or another live provider, pass credentials through your local environment. Do not commit tokens to this repository.

```bash
export LLM_PROVIDER=github
export GITHUB_TOKEN=<your-token>
docker compose up -d
```

## Project structure

```text
mcp-orchestrator-workbench/
|-- frontend/              # React frontend
|-- orchestrator-service/  # FastAPI orchestrator and agent/workflow logic
|-- mcp-server/            # FastMCP tool server
|-- logging-service/       # Execution logging service
|-- infrastructure/        # Azure deployment templates and scripts
|-- azure-pipelines.yml    # CI/CD pipeline skeleton
|-- docker-compose.yml     # Local development stack
`-- README.md
```

## Configuration

Important environment variables:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `mock`, `github`, or another configured provider |
| `GITHUB_TOKEN` | Optional token for GitHub Models; never commit this |
| `MCP_SERVER_URL` | MCP server endpoint used by orchestrator |
| `MAX_CONCURRENT_CALLS` | Maximum concurrent tool calls |
| `AZURE_AI_FOUNDRY_ENDPOINT` | Optional Azure AI endpoint |
| `AZURE_AI_FOUNDRY_KEY` | Optional Azure AI key; never commit this |
| `AZURE_AI_FOUNDRY_MODEL` | Optional Azure model name |

## Azure deployment

Azure deployment support is included as a prototype path. Treat the infrastructure files as examples to adapt, not as a one-click production template.

## Verification

Fast local checks:

```bash
cd frontend
npm install
npm run build
```

```bash
python -m unittest discover -s orchestrator-service/tests -v
python -m compileall orchestrator-service logging-service mcp-server
```

## Usage examples

### Chat Mode

```text
User: Get me two cat facts and summarize them.
System: Generates plan -> executes tools -> summarizes results.
```

### Agent Flow

```text
Agent: Researcher
Goal: Research and analyze the latest AI workflow patterns.
Agent: Thinks -> decides -> acts -> reports.
```

### Workflow Builder

```text
1. Add a tool node.
2. Add an analyst agent.
3. Connect tool output to agent input.
4. Execute and inspect logs.
```

## Positioning

> A prototype workbench for agentic workflow orchestration using React, FastAPI, FastMCP, Docker Compose, and Azure Container Apps.

It should not be presented as production-ready until security, auth, deployment, and test coverage are tightened.
