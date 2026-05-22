# Quick Start Guide

## Setup Instructions

### 1. Fixed Issues
✅ **Dockerfile Issues**: Fixed path problems in both `mcp-server` and `orchestrator` Dockerfiles
✅ **Frontend Dependencies**: Updated React Flow to latest version (`@xyflow/react`)
✅ **LLM Integration**: Added Ollama service with lightweight Phi-3 Mini model
✅ **Missing Dependencies**: Added `requests` library to orchestrator service
✅ **CORS Issues**: Added proper CORS middleware to orchestrator service
✅ **Professional UI**: Complete redesign with modern, polished interface
✅ **Build System**: All services now build successfully

### 2. Choose Your LLM Provider

#### Option A: Mock Mode (Quickest - No LLM needed) ⭐ RECOMMENDED
```bash
set LLM_PROVIDER=mock
docker-compose restart orchestrator
```
**Use this option to test the beautiful interface immediately!**

#### Option B: Local LLM (For tiny computers - 637MB model)
```bash
# Step 1: Start services
docker-compose up -d

# Step 2: Pull lightweight TinyLlama model (only 637MB!)
docker exec mcp_poc-ollama-1 ollama pull tinyllama

# Step 3: Use local LLM
set LLM_PROVIDER=local
docker-compose restart orchestrator
```

#### Option C: Azure AI Foundry (Production)
```bash
# Set your Azure credentials
set LLM_PROVIDER=azure
set AZURE_AI_ENDPOINT=https://your-endpoint.openai.azure.com/
set AZURE_AI_KEY=your-api-key
set AZURE_AI_DEPLOYMENT=your-deployment-name

docker-compose up
```

### 3. Access the Application
- **Frontend**: http://localhost:3000
- **Orchestrator API**: http://localhost:8100
- **MCP Server**: http://localhost:8000
- **Ollama** (if using local): http://localhost:11434

### 4. Test the Setup
1. Open http://localhost:3000
2. Enter a goal like: "Get me a random cat fact"
3. The system will generate a plan and execute it
4. Watch the execution progress in the graph visualization

## Architecture
- **mcp-server** (port 8000): Exposes tools including `cat_fact` and `echo`
- **orchestrator** (port 8100): LLM-driven planner and executor with WebSocket updates
- **frontend** (port 3000): React app with react-flow graph visualization
- **ollama** (port 11434): Local LLM service with Phi-3 Mini model

## Environment Configuration
Copy `.env.example` to `.env` and adjust settings as needed.