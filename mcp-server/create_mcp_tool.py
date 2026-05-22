#!/usr/bin/env python3
"""
MCP Tool Creator - Interactive CLI
Quickly create new MCP tools with guided prompts
"""

import json
import sys
from typing import Dict, Any, List

# Add app directory to path
sys.path.insert(0, 'app')

from utils.mcp_helper import quick_create_tool, validate_tool


def get_user_input(prompt: str, default: str = "") -> str:
    """Get input from user with optional default."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()

    if not response:
        return default

    return response in ['y', 'yes']


def collect_parameter() -> Dict[str, Any]:
    """Collect a single parameter definition from user."""
    print("\n--- Parameter Definition ---")

    name = get_user_input("Parameter name (snake_case)")
    while not name or ' ' in name:
        print("Error: Parameter name must be non-empty and use snake_case (no spaces)")
        name = get_user_input("Parameter name (snake_case)")

    description = get_user_input("Parameter description", "No description provided")

    print("\nParameter type:")
    print("  1. string")
    print("  2. integer")
    print("  3. number (float)")
    print("  4. boolean")
    print("  5. array")
    print("  6. object")

    type_choice = get_user_input("Select type (1-6)", "1")
    type_map = {
        "1": "string",
        "2": "integer",
        "3": "number",
        "4": "boolean",
        "5": "array",
        "6": "object"
    }
    param_type = type_map.get(type_choice, "string")

    required = get_yes_no("Is this parameter required?", True)

    param_def = {
        "type": param_type,
        "description": description,
        "required": required
    }

    if not required:
        has_default = get_yes_no("Provide a default value?", True)
        if has_default:
            default_str = get_user_input(f"Default value ({param_type})")
            # Convert to appropriate type
            if param_type == "integer":
                param_def["default"] = int(default_str) if default_str else 0
            elif param_type == "number":
                param_def["default"] = float(default_str) if default_str else 0.0
            elif param_type == "boolean":
                param_def["default"] = default_str.lower() in ['true', 'yes', '1']
            else:
                param_def["default"] = default_str

    return name, param_def


def collect_example() -> Dict[str, Any]:
    """Collect a single example from user."""
    print("\n--- Example Definition ---")

    description = get_user_input("Example description", "Example usage")

    print("\nEnter input parameters as JSON:")
    print('Example: {"param1": "value1", "param2": 42}')

    while True:
        input_json = get_user_input("Input JSON")
        try:
            input_params = json.loads(input_json)
            break
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON - {e}")
            if not get_yes_no("Try again?", True):
                input_params = {}
                break

    print("\nEnter expected output as JSON:")
    print('Example: {"status": "success", "result": "processed"}')

    while True:
        output_json = get_user_input("Output JSON", '{"status": "success"}')
        try:
            expected_output = json.loads(output_json)
            break
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON - {e}")
            if not get_yes_no("Try again?", True):
                expected_output = {"status": "success"}
                break

    return {
        "description": description,
        "input": {
            "raw_params": input_params
        },
        "expected_output": expected_output
    }


def main():
    """Main interactive tool creation flow."""
    print("=" * 60)
    print("MCP Tool Creator - Interactive CLI")
    print("=" * 60)
    print("\nThis wizard will guide you through creating a new MCP tool.")
    print("Press Ctrl+C at any time to cancel.\n")

    try:
        # Collect basic tool information
        print("\n=== Basic Tool Information ===\n")

        tool_name = get_user_input("Tool name (snake_case, e.g., 'weather_api')")
        while not tool_name or ' ' in tool_name or '-' in tool_name:
            print("Error: Tool name must use snake_case (underscores, no spaces or hyphens)")
            tool_name = get_user_input("Tool name (snake_case)")

        description = get_user_input(
            "Tool description (one line)",
            f"MCP tool for {tool_name.replace('_', ' ')}"
        )

        # Collect parameters
        print("\n=== Parameters ===\n")
        print("Define the parameters your tool accepts.")

        parameters = {}
        while True:
            param_name, param_def = collect_parameter()
            parameters[param_name] = param_def

            if not get_yes_no("\nAdd another parameter?", False):
                break

        if not parameters:
            print("\nWarning: Tool has no parameters. It will be a parameterless function.")

        # Collect examples (optional)
        print("\n=== Examples (Optional) ===\n")
        print("Provide usage examples to help with DSPy optimization.")

        examples = []
        if get_yes_no("Add usage examples?", True):
            while True:
                example = collect_example()
                examples.append(example)

                if not get_yes_no("\nAdd another example?", False):
                    break

        # Show summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"\nTool Name: {tool_name}")
        print(f"Description: {description}")
        print(f"\nParameters ({len(parameters)}):")
        for param_name, param_def in parameters.items():
            required = "required" if param_def.get("required", True) else "optional"
            default = f" (default: {param_def['default']})" if "default" in param_def else ""
            print(f"  - {param_name}: {param_def['type']} ({required}){default}")
            print(f"    {param_def.get('description', 'No description')}")

        if examples:
            print(f"\nExamples: {len(examples)}")
            for i, ex in enumerate(examples, 1):
                print(f"  {i}. {ex['description']}")

        # Confirm and create
        print("\n" + "=" * 60)
        if not get_yes_no("\nCreate this tool?", True):
            print("Cancelled.")
            return

        # Create the tool
        print("\nCreating tool files...")
        result = quick_create_tool(
            name=tool_name,
            description=description,
            parameters=parameters,
            examples=examples if examples else None
        )

        # Display results
        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"\nTool '{tool_name}' created successfully!\n")
        print(f"Files created:")
        print(f"  ✓ Python file: {result['tool_file']}")
        print(f"  ✓ Config file: {result['config_file']}")

        print("\n" + "=" * 60)
        print("NEXT STEPS")
        print("=" * 60)
        print("\n1. Edit the generated Python file to implement your tool logic:")
        print(f"   {result['tool_file']}")

        print("\n2. Register your tool in the MCP server:")
        print("   - Open: mcp-server/app/server.py")
        print(f"   - Add import: from tools.{tool_name} import {tool_name}")
        print("   - Add to tools list:")
        print("\n   Schema to add:")
        print("   " + "-" * 50)
        schema_json = json.dumps(result['schema'], indent=4)
        for line in schema_json.split('\n'):
            print(f"   {line}")
        print("   " + "-" * 50)

        print("\n   - Add to tool execution section:")
        print(f'''
   if tool_name == "{tool_name}":
       result = {tool_name}(
           {', '.join(f'{p}=request.parameters.get("{p}")' for p in parameters.keys())}
       )
       return result
''')

        print("\n3. Rebuild and restart the MCP server:")
        print("   docker-compose up -d --build mcp-server")

        print("\n4. Test your tool:")
        print("   - Use the frontend UI at http://localhost:3000")
        print("   - Or test directly with curl:")
        print(f'''
   curl -X POST http://localhost:8000/tools/{tool_name} \\
     -H "Content-Type: application/json" \\
     -d '{{"parameters": {json.dumps({p: "test_value" for p in list(parameters.keys())[:1]})}}}'
''')

        print("\n5. Optimize with DSPy:")
        print("   - Navigate to DSPy Optimizer in the UI")
        print("   - Run 'Bulk Optimization' to train your tool")
        print("   - Monitor metrics in the History tab")

        print("\n" + "=" * 60)
        print(f"Happy coding! Your tool '{tool_name}' is ready to implement.")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
