# MCP Tools - Quick Reference

## 📁 Documentation Locations

| Document | Location | Purpose |
|----------|----------|---------|
| **Main Guide** | `docs/CREATE_MCP_GUIDE.md` | Complete guide with architecture, examples, troubleshooting |
| **Quick Start** | `mcp-server/README_MCP_CREATION.md` | Quick reference for creating tools |
| **Helper API** | `mcp-server/app/utils/mcp_helper.py` | Programmatic tool creation |

## 🚀 CLI Tools

### 1. Full Tool Creator (Python + YAML)

Creates complete MCP tool with Python code and YAML config:

```bash
cd mcp-server
python create_mcp_tool.py
```

**What it does:**
- ✅ Generates Python tool file
- ✅ Generates YAML configuration
- ✅ Provides registration instructions
- ✅ Interactive prompts for all settings

**Example Output:**
```
Files created:
  ✓ Python file: app/tools/my_tool.py
  ✓ Config file: app/tool_configs/my_tool.yaml

Next steps:
  1. Implement tool logic in my_tool.py
  2. Register in server.py
  3. Rebuild: docker-compose up -d --build mcp-server
```

---

### 2. YAML-Only Generator

Creates just the YAML config for existing tools:

```bash
cd mcp-server
python generate_yaml.py
```

**What it does:**
- ✅ Generates YAML configuration only
- ✅ Faster for adding configs to existing tools
- ✅ Interactive or batch mode

**Use when:**
- You already have the Python tool file
- You want to add optimization config to existing tool
- You're updating tool configurations

---

## 📝 YAML Configuration Structure

### Basic Template

```yaml
tool:
  name: my_tool
  description: "What the tool does"
  version: "1.0.0"

parameters:
  name_mappings:
    # Map common wrong names to correct ones
    "wrong_name": "correct_name"
    "input": "text"
    "value": "amount"

  smart_defaults:
    optional_param:
      strategy: "context_aware"
      default_value: 10
      fallback_values: [5, 10, 20]

examples:
  - description: "Basic usage"
    input:
      raw_params:
        text: "Hello world"
        count: 5
    expected_output:
      status: "success"
      result: "Processed"

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
  last_updated: null
```

---

## 🔧 Programmatic Usage

### Quick Create (Python + YAML)

```python
from utils.mcp_helper import quick_create_tool

result = quick_create_tool(
    name="my_tool",
    description="What my tool does",
    parameters={
        "text": {
            "type": "string",
            "description": "Text to process",
            "required": True
        },
        "count": {
            "type": "integer",
            "description": "Number of times",
            "default": 1
        }
    },
    examples=[
        {
            "description": "Basic example",
            "input": {
                "raw_params": {"text": "hello", "count": 2}
            },
            "expected_output": {
                "status": "success",
                "result": "processed"
            }
        }
    ]
)

print(f"Created: {result['tool_file']}")
print(f"Config: {result['config_file']}")
```

### YAML-Only Creation

```python
from utils.mcp_helper import MCPHelper

helper = MCPHelper()

# Create config
config = helper.create_config_template(
    tool_name="my_tool",
    description="What it does",
    parameters={
        "param1": {"type": "string", "description": "First param"}
    }
)

# Save to file
path = helper.save_config_file("my_tool", config)
print(f"Saved to: {path}")
```

---

## 📊 Common YAML Patterns

### 1. Parameter Name Mappings

Fix common parameter naming mistakes:

```yaml
parameters:
  name_mappings:
    "place": "location"          # weather_tool
    "sentence": "text"            # translate_tool
    "formula": "expression"       # calculate_tool
    "q": "query"                  # search_tool
    "lang": "target_language"     # translate_tool
```

### 2. Smart Defaults

Provide intelligent default values:

```yaml
parameters:
  smart_defaults:
    units:
      strategy: "context_aware"
      default_value: "celsius"
      fallback_values: ["celsius", "fahrenheit"]

    limit:
      strategy: "user_preference"
      default_value: 10
      fallback_values: [5, 10, 20, 50]
```

### 3. Error Recovery Strategies

Define how to recover from errors:

```yaml
error_recovery:
  strategies:
    - error_pattern: "missing.*required.*parameter"
      recovery_action: "use_context_to_fill"
      retry: true

    - error_pattern: "invalid.*format"
      recovery_action: "auto_format_and_retry"
      retry: true

    - error_pattern: "timeout"
      recovery_action: "reduce_complexity"
      retry: true
```

### 4. Training Examples

Provide diverse examples for DSPy optimization:

```yaml
examples:
  # Example 1: Basic usage
  - description: "Simple query"
    input:
      raw_params:
        query: "Python tutorials"
    expected_output:
      status: "success"
      results: ["..."]

  # Example 2: With wrong parameter names
  - description: "Wrong param names (will be fixed)"
    input:
      raw_params:
        q: "machine learning"  # Wrong name
    expected_output:
      status: "success"
      corrected_params:
        query: "machine learning"  # Correct name

  # Example 3: Edge case
  - description: "Empty input handling"
    input:
      raw_params: {}
    expected_output:
      status: "error"
      error: "Missing required parameter"
```

---

## 🎯 Workflow Examples

### Create New Tool with YAML

```bash
# Option 1: Interactive CLI (recommended)
cd mcp-server
python create_mcp_tool.py

# Option 2: Python script
python -c "
from utils.mcp_helper import quick_create_tool
quick_create_tool(
    name='my_new_tool',
    description='Does something useful',
    parameters={'input': {'type': 'string'}}
)
"
```

### Add YAML to Existing Tool

```bash
# Option 1: Interactive
cd mcp-server
python generate_yaml.py

# Option 2: Script
python -c "
from utils.mcp_helper import MCPHelper
helper = MCPHelper()
config = helper.create_config_template('existing_tool', 'Description')
helper.save_config_file('existing_tool', config)
"
```

### Validate Tool Structure

```bash
python -c "
from utils.mcp_helper import validate_tool
result = validate_tool('my_tool')
print('Valid:', result['valid'])
print('Errors:', result['errors'])
"
```

---

## 🔍 Where Files Go

```
mcp-server/
├── app/
│   ├── tools/
│   │   ├── my_tool.py          ← Python implementation
│   │   ├── weather_tool.py
│   │   └── ...
│   │
│   └── tool_configs/
│       ├── my_tool.yaml        ← YAML configuration
│       ├── weather_tool.yaml
│       └── ...
│
├── create_mcp_tool.py          ← Full tool creator CLI
├── generate_yaml.py            ← YAML-only generator CLI
└── README_MCP_CREATION.md
```

---

## 🚀 After Creating a Tool

### 1. Register in server.py

```python
# Add import
from tools.my_tool import my_tool

# Add to tools list
{
    "name": "my_tool",
    "description": "What it does",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
}

# Add to execution section
@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest):
    if tool_name == "my_tool":
        result = my_tool(
            param1=request.parameters.get("param1")
        )
        return result
```

### 2. Rebuild and Test

```bash
# Rebuild MCP server
docker-compose up -d --build mcp-server

# Test with curl
curl -X POST http://localhost:8000/tools/my_tool \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"param1": "test"}}'
```

### 3. Optimize with DSPy

1. Open frontend: http://localhost:3000
2. Click "DSPy Optimizer"
3. Go to "Tool Configs" tab
4. Verify your tool's config is loaded
5. Run "Bulk Optimization"
6. Check "History" tab for metrics

---

## 📚 Additional Resources

- **Full Documentation**: `docs/CREATE_MCP_GUIDE.md`
- **Quick Reference**: `mcp-server/README_MCP_CREATION.md`
- **Helper API Docs**: See docstrings in `mcp-server/app/utils/mcp_helper.py`
- **Example Tools**: See existing tools in `mcp-server/app/tools/`
- **Example Configs**: See configs in `mcp-server/app/tool_configs/`

---

## 💡 Tips

1. **Start with CLI**: Use `create_mcp_tool.py` for first-time creation
2. **YAML First**: Create YAML configs early for better optimization
3. **Examples Matter**: More examples = better DSPy optimization
4. **Test Locally**: Test tools with curl before frontend integration
5. **Version Control**: Commit both .py and .yaml files together

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Tool not found | Check registration in server.py |
| YAML not loaded | Check filename matches tool name |
| Import errors | Rebuild container: `docker-compose up -d --build` |
| Parameter errors | Check YAML name_mappings |
| No optimization | Verify YAML has examples and optimization.enabled=true |

For more help, see `docs/CREATE_MCP_GUIDE.md` troubleshooting section.
