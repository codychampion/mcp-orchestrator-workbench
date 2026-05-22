# Guide to Creating New MCP Tools

## Table of Contents
1. [Overview](#overview)
2. [MCP Architecture](#mcp-architecture)
3. [Creating a New MCP Tool](#creating-a-new-mcp-tool)
4. [Configuration Files](#configuration-files)
5. [Testing Your MCP](#testing-your-mcp)
6. [DSPy Optimization](#dspy-optimization)
7. [Examples](#examples)

## Overview

MCP (Model Context Protocol) is a universal protocol that enables AI agents to interact with external tools and services. In this system, MCP tools are Python functions that can be called by the orchestrator to perform specific tasks.

### Key Concepts

- **MCP Tool**: A function that performs a specific task (e.g., get weather, calculate, search)
- **Tool Schema**: JSON schema defining the tool's name, description, and parameters
- **Tool Configuration**: YAML file containing optimization settings and examples
- **DSPy Optimization**: Machine learning-based optimization of tool calls

## MCP Architecture

### System Components

```
┌─────────────┐
│   Frontend  │  (React UI - user interface)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Orchestrator│  (Python FastAPI - workflow management)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ MCP Server  │  (Python FastAPI - tool execution)
└─────────────┘
```

### Request Flow

1. User sends a goal from Frontend
2. Orchestrator generates a workflow plan
3. Orchestrator calls MCP tools via HTTP
4. MCP Server executes tools and returns results
5. Results flow back to user through Orchestrator

## Creating a New MCP Tool

### Step 1: Define Your Tool Function

Create a new file in `mcp-server/app/tools/your_tool.py`:

```python
from typing import Dict, Any

def your_tool_function(param1: str, param2: int = 10) -> Dict[str, Any]:
    """
    Brief description of what your tool does.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter (optional)

    Returns:
        Dictionary containing the result
    """
    try:
        # Your tool logic here
        result = f"Processed {param1} with value {param2}"

        return {
            "status": "success",
            "result": result,
            "details": {
                "param1": param1,
                "param2": param2
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### Step 2: Register Your Tool

Add your tool to `mcp-server/app/server.py`:

```python
from tools.your_tool import your_tool_function

# In the tools list, add your tool schema
{
    "name": "your_tool",
    "description": "Brief description for AI to understand when to use this tool",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of param1"
            },
            "param2": {
                "type": "integer",
                "description": "Description of param2",
                "default": 10
            }
        },
        "required": ["param1"]
    }
}

# In the tool execution section, add your tool handler
@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest):
    if tool_name == "your_tool":
        result = your_tool_function(
            param1=request.parameters.get("param1"),
            param2=request.parameters.get("param2", 10)
        )
        return result
```

### Step 3: Create Tool Configuration (Optional but Recommended)

Create a YAML configuration file at `mcp-server/app/tool_configs/your_tool.yaml`:

```yaml
tool:
  name: your_tool
  description: "Brief description of your tool"
  version: "1.0.0"

parameters:
  name_mappings:
    # Common parameter name variations
    "value": "param1"
    "input": "param1"
    "count": "param2"
    "number": "param2"

  smart_defaults:
    param2:
      strategy: "context_aware"
      default_value: 10
      fallback_values: [5, 10, 20]

examples:
  - description: "Basic usage example"
    input:
      raw_params:
        param1: "test"
        param2: 10
    expected_output:
      status: "success"
      result: "Processed test with value 10"

  - description: "Example with default param2"
    input:
      raw_params:
        param1: "hello"
    expected_output:
      status: "success"
      result: "Processed hello with value 10"

error_recovery:
  strategies:
    - error_pattern: "invalid.*param1"
      recovery_action: "validate_and_sanitize"
      retry: true
    - error_pattern: ".*out of range.*"
      recovery_action: "use_default_param2"
      retry: true

optimization:
  enabled: true
  accuracy_metrics:
    successful_calls: 0
    failed_calls: 0
    parameter_correction_rate: 0.0
    error_recovery_rate: 0.0
  last_updated: null
```

## Configuration Files

### Tool Configuration Structure

#### `tool` Section
- `name`: Tool identifier (must match function name)
- `description`: Clear description for AI understanding
- `version`: Tool version for tracking changes

#### `parameters` Section
- `name_mappings`: Map common variations to canonical parameter names
- `smart_defaults`: Define intelligent default value strategies

#### `examples` Section
- Provide real-world usage examples
- Include both input and expected output
- Used for DSPy training and validation

#### `error_recovery` Section
- Define error patterns and recovery strategies
- Specify whether to retry after recovery
- Helps DSPy learn from failures

#### `optimization` Section
- Enable/disable DSPy optimization
- Track accuracy metrics
- Record optimization history

## Testing Your MCP

### Manual Testing

1. Start the MCP server:
```bash
docker-compose up -d mcp-server
```

2. Test your tool with curl:
```bash
curl -X POST http://localhost:8000/tools/your_tool \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "param1": "test",
      "param2": 15
    }
  }'
```

### Integration Testing

1. Start all services:
```bash
docker-compose up -d
```

2. Use the frontend to test:
   - Navigate to http://localhost:3000
   - Enter a goal that should use your tool
   - Check the workflow execution

3. Verify in DSPy Optimizer:
   - Click "DSPy Optimizer" button
   - Check "Tool Configs" tab for your tool
   - Run "Bulk Optimization" to train

## DSPy Optimization

### What is DSPy?

DSPy is a framework for optimizing LLM-based systems through machine learning. In our system, DSPy:

1. **Parameter Enhancement**: Fixes incorrect parameter names and generates missing values
2. **Error Recovery**: Learns from failures to automatically recover
3. **Plan Generation**: Optimizes workflow planning
4. **Tool Selection**: Improves tool selection accuracy

### Enabling Optimization for Your Tool

1. Create a comprehensive YAML configuration (see Step 3 above)
2. Provide diverse examples in the `examples` section
3. Define error recovery strategies
4. Run bulk optimization from the DSPy Optimizer UI

### Best Practices

- **Provide 5-10 diverse examples** covering common use cases
- **Include edge cases** in your examples
- **Map common parameter variations** to help with name corrections
- **Define smart defaults** for optional parameters
- **Specify error recovery strategies** for known failure modes

## Examples

### Example 1: Simple Calculator Tool

```python
# mcp-server/app/tools/simple_calc.py
def simple_calc(operation: str, a: float, b: float) -> dict:
    """Perform basic arithmetic operations."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None
    }

    if operation not in operations:
        return {"status": "error", "error": f"Unknown operation: {operation}"}

    result = operations[operation](a, b)
    if result is None:
        return {"status": "error", "error": "Division by zero"}

    return {
        "status": "success",
        "result": result,
        "operation": operation,
        "inputs": {"a": a, "b": b}
    }
```

### Example 2: Data Fetcher Tool

```python
# mcp-server/app/tools/data_fetcher.py
import requests
from typing import Dict, Any, Optional

def fetch_data(url: str, timeout: int = 30, headers: Optional[Dict] = None) -> Dict[str, Any]:
    """Fetch data from a URL."""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers=headers or {}
        )
        response.raise_for_status()

        return {
            "status": "success",
            "data": response.json(),
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error": "Request timeout",
            "url": url
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": str(e),
            "url": url
        }
```

### Example 3: File Processor Tool

```python
# mcp-server/app/tools/file_processor.py
import os
from typing import Dict, Any, List

def process_file(filepath: str, action: str = "read", encoding: str = "utf-8") -> Dict[str, Any]:
    """Process a file (read, list directory, check existence)."""
    try:
        if action == "read":
            if not os.path.exists(filepath):
                return {"status": "error", "error": "File not found"}

            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()

            return {
                "status": "success",
                "action": "read",
                "content": content,
                "size": len(content),
                "filepath": filepath
            }

        elif action == "list":
            if not os.path.isdir(filepath):
                return {"status": "error", "error": "Not a directory"}

            files = os.listdir(filepath)
            return {
                "status": "success",
                "action": "list",
                "files": files,
                "count": len(files),
                "directory": filepath
            }

        elif action == "exists":
            exists = os.path.exists(filepath)
            return {
                "status": "success",
                "action": "exists",
                "exists": exists,
                "filepath": filepath
            }

        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "filepath": filepath
        }
```

## Helper Functions

Use the MCP Helper utility to generate tool templates:

```python
from utils.mcp_helper import MCPHelper

helper = MCPHelper()

# Generate a new tool template
helper.create_tool_template(
    name="your_tool",
    description="What your tool does",
    parameters={
        "param1": {"type": "string", "description": "First parameter"},
        "param2": {"type": "integer", "description": "Second parameter", "default": 10}
    }
)

# Generate YAML configuration
helper.create_config_template(
    tool_name="your_tool",
    examples=[
        {
            "description": "Example 1",
            "input": {"param1": "test"},
            "output": {"status": "success"}
        }
    ]
)
```

## Troubleshooting

### Common Issues

1. **Tool not found**: Ensure tool is registered in `server.py`
2. **Parameter errors**: Check parameter names match schema
3. **Import errors**: Verify all dependencies are in `requirements.txt`
4. **Optimization not working**: Ensure YAML config exists and has examples

### Debug Tips

- Check MCP server logs: `docker-compose logs mcp-server`
- Check orchestrator logs: `docker-compose logs orchestrator`
- Use the frontend's status indicator to verify connectivity
- Test tools individually before integration

## Next Steps

1. Read existing tool implementations in `mcp-server/app/tools/`
2. Study existing YAML configs in `mcp-server/app/tool_configs/`
3. Use the MCP Helper utility to generate templates
4. Test thoroughly before deploying
5. Monitor optimization metrics in DSPy Optimizer

## Resources

- MCP Specification: https://modelcontextprotocol.io
- DSPy Documentation: https://dspy-docs.vercel.app
- FastAPI Documentation: https://fastapi.tiangolo.com
- This Project's Architecture: See `docs/ARCHITECTURE.md`
