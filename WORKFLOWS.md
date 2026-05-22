# Workflow Save/Load Guide

## Overview

Workflows allow you to define reusable task execution flows that can be saved as JSON and loaded later. Each workflow consists of nodes (tool calls or agent executions) and edges (dependencies between nodes).

## Workflow Structure

A workflow JSON file has the following structure:

```json
{
  "workflow_id": "unique-workflow-id",
  "nodes": [
    {
      "id": "node1",
      "type": "tool" | "agent",
      "config": {
        "tool": "tool_name",           // for type: "tool"
        "params": { ... },             // for type: "tool"
        "agent_type": "executor",      // for type: "agent"
        "goal": "agent goal"           // for type: "agent"
      }
    }
  ],
  "edges": [
    {
      "from": "node1",
      "to": "node2"
    }
  ],
  "metadata": {
    "created_at": "ISO 8601 timestamp",
    "description": "Workflow description",
    "version": "1.0"
  }
}
```

## API Endpoints

### 1. Create a Workflow

**POST** `/workflow/create`

```bash
curl -X POST http://localhost:8100/workflow/create \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [
      {"id": "n1", "type": "tool", "config": {"tool": "cat_fact", "params": {}}},
      {"id": "n2", "type": "tool", "config": {"tool": "echo", "params": {"text": "Done!"}}}
    ],
    "edges": [
      {"from": "n1", "to": "n2"}
    ]
  }'
```

**Response:**
```json
{
  "workflow_id": "abc123...",
  "nodes": 2,
  "edges": 1
}
```

### 2. Execute a Workflow

**POST** `/workflow/{workflow_id}/execute`

```bash
curl -X POST http://localhost:8100/workflow/abc123.../execute
```

**Response:**
```json
{
  "workflow_id": "abc123...",
  "status": "started"
}
```

### 3. Save (Export) a Workflow

**GET** `/workflow/{workflow_id}/save`

```bash
curl http://localhost:8100/workflow/abc123.../save
```

**Response:**
```json
{
  "status": "success",
  "workflow": {
    "workflow_id": "abc123...",
    "nodes": [...],
    "edges": [...],
    "metadata": {...}
  }
}
```

**Save to file:**
```bash
curl http://localhost:8100/workflow/abc123.../save > my-workflow.json
```

### 4. Load (Import) a Workflow

**POST** `/workflow/load`

```bash
curl -X POST http://localhost:8100/workflow/load \
  -H "Content-Type: application/json" \
  -d @example-workflow.json
```

Or from a workflow object:
```bash
curl -X POST http://localhost:8100/workflow/load \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "workflow_id": "my-workflow",
      "nodes": [...],
      "edges": [...]
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "workflow_id": "my-workflow",
  "nodes": 4,
  "edges": 3
}
```

### 5. Get Workflow Status

**GET** `/workflow/{workflow_id}`

```bash
curl http://localhost:8100/workflow/abc123...
```

**Response:**
```json
{
  "workflow_id": "abc123...",
  "nodes": {
    "node1": {
      "type": "tool",
      "status": "success",
      "result": "output",
      "error": null
    }
  },
  "edges": [...],
  "state": {...}
}
```

## Example Workflow

See `example-workflow.json` for a complete example. This workflow:

1. Gets a cat fact using the `cat_fact` tool
2. Echoes a message using the `echo` tool
3. Summarizes the cat fact using the `summarize` tool
4. Saves the summary using the `save_fact` tool

The workflow demonstrates:
- Multiple nodes with dependencies
- Parallel execution (nodes 2 and 3 run in parallel after node 1)
- Sequential execution (node 4 waits for node 3)
- **LLM-powered parameter transformation** (node 3 and 4 parameters are automatically filled from previous nodes' outputs)

## LLM-Powered Parameter Transformation

When a node has dependencies, the workflow manager automatically uses an LLM to transform the outputs from dependency nodes into the correct parameters for the current node.

**How it works:**
1. Workflow collects all outputs from completed dependency nodes
2. Fetches the tool's input schema from the MCP server
3. Uses LLM to intelligently map dependency outputs to tool parameters
4. Executes the tool with the transformed parameters

**Example:**
- Node 1 outputs: `{"result": "Cats can rotate their ears 180 degrees."}`
- Node 3 needs: `{"text": "Cats can rotate their ears 180 degrees."}`
- LLM automatically extracts `result` from node 1 and maps it to `text` for node 3

This means you can define workflows without hardcoding all parameter mappings!

## Complete Example Usage

```bash
# 1. Load the example workflow
curl -X POST http://localhost:8100/workflow/load \
  -H "Content-Type: application/json" \
  -d @example-workflow.json

# Response: {"status": "success", "workflow_id": "example-cat-facts-workflow", ...}

# 2. Execute the workflow
curl -X POST http://localhost:8100/workflow/example-cat-facts-workflow/execute

# 3. Check status (wait a few seconds for execution)
curl http://localhost:8100/workflow/example-cat-facts-workflow

# 4. Save the workflow (with execution results)
curl http://localhost:8100/workflow/example-cat-facts-workflow/save > executed-workflow.json
```

## WebSocket Real-Time Updates

You can connect to a workflow via WebSocket to receive real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8100/ws/workflow/abc123...')

ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  console.log('Update:', update)

  // Update types:
  // - workflow_start: Workflow execution started
  // - node_start: Node execution started
  // - node_complete: Node execution completed
  // - node_error: Node execution failed
  // - input_transformed: LLM transformed parameters for node
  // - workflow_complete: Workflow execution finished
}
```

## Tips

1. **Node IDs**: Use descriptive IDs like "fetch_data", "process", "save_result"
2. **Tool Nodes**: Specify the tool name and parameters
3. **Agent Nodes**: Specify agent type and goal
4. **Dependencies**: Edges define execution order (from → to)
5. **Parallel Execution**: Nodes with no dependencies between them run in parallel
6. **LLM Transformation**: Don't worry about exact parameter mapping - the LLM handles it!

## Troubleshooting

### Workflow fails to load
- Check JSON syntax is valid
- Ensure all node IDs in edges exist in nodes array
- Verify tool names are available in MCP server

### Node execution fails
- Check tool parameters match the tool's input schema
- View execution logs: `docker-compose logs orchestrator`
- Use `/workflow/{id}` endpoint to see error details

### LLM transformation issues
- Check that dependency nodes completed successfully
- Verify tool schemas are available from MCP server
- Review orchestrator logs for transformation details: `[WORKFLOW] input_transformed`
