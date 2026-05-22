# Creating MCP Tools - Quick Start Guide

This guide shows you how to quickly create new MCP tools using the provided helper utilities.

## Table of Contents

- [Quick Start - Interactive CLI](#quick-start---interactive-cli)
- [Programmatic Creation](#programmatic-creation)
- [Manual Creation](#manual-creation)
- [Tool Validation](#tool-validation)
- [Examples](#examples)

## Quick Start - Interactive CLI

The easiest way to create a new MCP tool is using the interactive CLI:

```bash
cd mcp-server
python create_mcp_tool.py
```

The wizard will guide you through:
1. Naming your tool
2. Writing a description
3. Defining parameters (name, type, required/optional, defaults)
4. Adding usage examples
5. Generating all necessary files

### Example Session

```
MCP Tool Creator - Interactive CLI
=====================================

Tool name (snake_case): weather_forecast
Tool description: Get weather forecast for a location

=== Parameters ===

Parameter name: location
Parameter description: City name or coordinates
Parameter type: [1] string
Is this parameter required? [Y/n]: y

Add another parameter? [y/N]: y

Parameter name: days
Parameter description: Number of days to forecast
Parameter type: [2] integer
Is this parameter required? [Y/n]: n
Provide a default value? [Y/n]: y
Default value: 7

=== Examples ===

Add usage examples? [Y/n]: y

Example description: Get 7-day forecast for Seattle
Input JSON: {"location": "Seattle, WA", "days": 7}
Output JSON: {"status": "success", "forecast": [...]}

Create this tool? [Y/n]: y

SUCCESS! Tool 'weather_forecast' created.
```

## Programmatic Creation

You can also create tools programmatically using the helper functions:

### Method 1: Quick Create

```python
from utils.mcp_helper import quick_create_tool

result = quick_create_tool(
    name="my_tool",
    description="What my tool does",
    parameters={
        "input_text": {
            "type": "string",
            "description": "Text to process",
            "required": True
        },
        "max_length": {
            "type": "integer",
            "description": "Maximum length",
            "default": 100
        }
    },
    examples=[
        {
            "description": "Basic usage",
            "input": {
                "raw_params": {
                    "input_text": "Hello world",
                    "max_length": 50
                }
            },
            "expected_output": {
                "status": "success",
                "result": "Processed: Hello world"
            }
        }
    ]
)

print(f"Created: {result['tool_file']}")
print(f"Config: {result['config_file']}")
```

### Method 2: Using MCPHelper Class

```python
from utils.mcp_helper import MCPHelper

helper = MCPHelper()

# Generate tool template
template = helper.create_tool_template(
    name="my_tool",
    description="What my tool does",
    parameters={
        "param1": {"type": "string", "description": "First parameter"}
    }
)

# Save to file
tool_path = helper.save_tool_file("my_tool", template)

# Generate configuration
config = helper.create_config_template(
    tool_name="my_tool",
    description="What my tool does",
    parameters={
        "param1": {"type": "string", "description": "First parameter"}
    }
)

# Save config
config_path = helper.save_config_file("my_tool", config)

# Generate JSON schema for registration
schema = helper.generate_tool_schema(
    name="my_tool",
    description="What my tool does",
    parameters={
        "param1": {"type": "string", "description": "First parameter"}
    }
)

print(schema)
```

## Manual Creation

If you prefer manual creation, follow these steps:

### Step 1: Create Tool Python File

Create `app/tools/my_tool.py`:

```python
from typing import Dict, Any

def my_tool(param1: str, param2: int = 10) -> Dict[str, Any]:
    """
    Tool description.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dictionary with status and result
    """
    try:
        # Your logic here
        result = f"Processed {param1} with {param2}"

        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### Step 2: Create Configuration File

Create `app/tool_configs/my_tool.yaml`:

```yaml
tool:
  name: my_tool
  description: "Tool description"
  version: "1.0.0"

parameters:
  name_mappings:
    "value": "param1"
    "input": "param1"

  smart_defaults:
    param2:
      strategy: "context_aware"
      default_value: 10

examples:
  - description: "Basic usage"
    input:
      raw_params:
        param1: "test"
        param2: 10
    expected_output:
      status: "success"
      result: "Processed test with 10"

error_recovery:
  strategies:
    - error_pattern: "invalid.*parameter"
      recovery_action: "validate_and_sanitize"
      retry: true

optimization:
  enabled: true
  accuracy_metrics:
    successful_calls: 0
    failed_calls: 0
    parameter_correction_rate: 0.0
    error_recovery_rate: 0.0
```

### Step 3: Register in Server

Edit `app/server.py`:

```python
# Add import
from tools.my_tool import my_tool

# Add to tools list
{
    "name": "my_tool",
    "description": "Tool description",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description"
            },
            "param2": {
                "type": "integer",
                "description": "Description",
                "default": 10
            }
        },
        "required": ["param1"]
    }
}

# Add to execution section
@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest):
    # ... existing code ...

    if tool_name == "my_tool":
        result = my_tool(
            param1=request.parameters.get("param1"),
            param2=request.parameters.get("param2", 10)
        )
        return result
```

## Tool Validation

Validate your tool structure:

```python
from utils.mcp_helper import validate_tool

validation = validate_tool("my_tool")

if validation["valid"]:
    print("✓ Tool is valid")
else:
    print("✗ Tool has errors:")
    for error in validation["errors"]:
        print(f"  - {error}")

if validation["warnings"]:
    print("Warnings:")
    for warning in validation["warnings"]:
        print(f"  - {warning}")
```

## Examples

### Example 1: Simple Text Processor

```python
from utils.mcp_helper import quick_create_tool

quick_create_tool(
    name="text_processor",
    description="Process and transform text",
    parameters={
        "text": {
            "type": "string",
            "description": "Text to process",
            "required": True
        },
        "operation": {
            "type": "string",
            "description": "Operation: uppercase, lowercase, reverse",
            "default": "uppercase"
        }
    },
    examples=[
        {
            "description": "Convert to uppercase",
            "input": {"raw_params": {"text": "hello", "operation": "uppercase"}},
            "expected_output": {"status": "success", "result": "HELLO"}
        },
        {
            "description": "Reverse text",
            "input": {"raw_params": {"text": "hello", "operation": "reverse"}},
            "expected_output": {"status": "success", "result": "olleh"}
        }
    ]
)
```

### Example 2: API Client Tool

```python
from utils.mcp_helper import quick_create_tool

quick_create_tool(
    name="api_client",
    description="Make HTTP requests to external APIs",
    parameters={
        "url": {
            "type": "string",
            "description": "API endpoint URL",
            "required": True
        },
        "method": {
            "type": "string",
            "description": "HTTP method (GET, POST, etc.)",
            "default": "GET"
        },
        "headers": {
            "type": "object",
            "description": "HTTP headers",
            "required": False
        },
        "timeout": {
            "type": "integer",
            "description": "Request timeout in seconds",
            "default": 30
        }
    },
    examples=[
        {
            "description": "GET request",
            "input": {
                "raw_params": {
                    "url": "https://api.example.com/data",
                    "method": "GET"
                }
            },
            "expected_output": {
                "status": "success",
                "data": {},
                "status_code": 200
            }
        }
    ]
)
```

### Example 3: Data Validator Tool

```python
from utils.mcp_helper import quick_create_tool

quick_create_tool(
    name="data_validator",
    description="Validate data against a schema",
    parameters={
        "data": {
            "type": "object",
            "description": "Data to validate",
            "required": True
        },
        "schema_type": {
            "type": "string",
            "description": "Type of schema: json, xml, csv",
            "default": "json"
        },
        "strict": {
            "type": "boolean",
            "description": "Strict validation mode",
            "default": False
        }
    },
    examples=[
        {
            "description": "Validate JSON data",
            "input": {
                "raw_params": {
                    "data": {"name": "John", "age": 30},
                    "schema_type": "json",
                    "strict": True
                }
            },
            "expected_output": {
                "status": "success",
                "valid": True,
                "errors": []
            }
        }
    ]
)
```

## Testing Your Tool

After creation, test your tool:

```bash
# Rebuild MCP server
docker-compose up -d --build mcp-server

# Test with curl
curl -X POST http://localhost:8000/tools/my_tool \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"param1": "test_value"}}'

# Or use the frontend UI
# Navigate to http://localhost:3000
# Enter a goal that uses your tool
```

## DSPy Optimization

After testing, optimize your tool with DSPy:

1. Open the frontend UI at http://localhost:3000
2. Click "DSPy Optimizer" button
3. Go to "Tool Configs" tab
4. Verify your tool's configuration is loaded
5. Go to "Overview" tab
6. Click "Run Bulk Optimization"
7. Monitor training progress
8. Check "History" tab for metrics

## Troubleshooting

### Tool Not Found

- Verify tool is imported in `server.py`
- Check function name matches tool name
- Rebuild MCP server container

### Parameter Errors

- Check parameter names match schema
- Verify required parameters are provided
- Check parameter types match definitions

### Import Errors

- Ensure all dependencies are in `requirements.txt`
- Rebuild container after adding dependencies

### Configuration Not Loading

- Check YAML syntax is valid
- Verify file is in `app/tool_configs/`
- Check file name matches tool name

## Further Reading

- See `docs/CREATE_MCP_GUIDE.md` for comprehensive documentation
- Check existing tools in `app/tools/` for examples
- Review YAML configs in `app/tool_configs/` for configuration examples

## Support

For issues or questions:
- Check the main documentation in `docs/`
- Review existing tool implementations
- Check MCP server logs: `docker-compose logs mcp-server`
