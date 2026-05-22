#!/usr/bin/env python3
"""
Quick YAML Config Generator
Generate YAML configuration for existing MCP tools
"""

import sys
import json
sys.path.insert(0, 'app')

from utils.mcp_helper import MCPHelper


def main():
    """Generate YAML config for a tool"""
    print("=" * 60)
    print("MCP YAML Config Generator")
    print("=" * 60)
    print("\nQuickly generate YAML configuration for existing tools\n")

    # Get tool name
    tool_name = input("Tool name (e.g., weather_tool): ").strip()
    if not tool_name:
        print("Error: Tool name required")
        return

    description = input(f"Description for {tool_name}: ").strip()
    if not description:
        description = f"MCP tool: {tool_name}"

    # Ask for parameters
    print("\n--- Parameters ---")
    print("Enter parameters in JSON format (or press Enter to skip)")
    print('Example: {"location": {"type": "string", "description": "City name"}}')

    params_json = input("\nParameters JSON (or Enter to skip): ").strip()
    parameters = {}
    if params_json:
        try:
            parameters = json.loads(params_json)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON, skipping parameters: {e}")

    # Ask for examples
    print("\n--- Examples ---")
    add_examples = input("Add usage examples? (y/N): ").strip().lower() == 'y'

    examples = []
    if add_examples:
        while True:
            print("\nExample:")
            example_desc = input("  Description: ").strip()
            if not example_desc:
                break

            print('  Input params (JSON): {"param1": "value1"}')
            input_json = input("  > ").strip()
            try:
                input_params = json.loads(input_json) if input_json else {}
            except json.JSONDecodeError:
                print("  Invalid JSON, skipping this example")
                continue

            print('  Expected output (JSON): {"status": "success"}')
            output_json = input("  > ").strip()
            try:
                expected_output = json.loads(output_json) if output_json else {"status": "success"}
            except json.JSONDecodeError:
                print("  Invalid JSON, using default")
                expected_output = {"status": "success"}

            examples.append({
                "description": example_desc,
                "input": {"raw_params": input_params},
                "expected_output": expected_output
            })

            if input("\n  Add another example? (y/N): ").strip().lower() != 'y':
                break

    # Generate YAML
    helper = MCPHelper()

    config = helper.create_config_template(
        tool_name=tool_name,
        description=description,
        parameters=parameters,
        examples=examples if examples else None
    )

    # Save to file
    config_path = helper.save_config_file(tool_name, config)

    # Display result
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"\nYAML config saved to: {config_path}")
    print(f"\nFile: app/tool_configs/{tool_name}.yaml")

    print("\n--- Configuration Preview ---")
    import yaml
    print(yaml.dump(config, default_flow_style=False, sort_keys=False))

    print("\n--- Next Steps ---")
    print("1. Edit the YAML file to customize settings")
    print("2. Restart the MCP server:")
    print("   docker-compose up -d --build mcp-server")
    print("3. The config will be automatically loaded")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
