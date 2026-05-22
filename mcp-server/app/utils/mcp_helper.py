"""
MCP Helper Utility
Provides functions to assist with creating new MCP tools
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime


class MCPHelper:
    """Helper class for creating and managing MCP tools."""

    def __init__(self, tools_dir: str = "app/tools", configs_dir: str = "app/tool_configs"):
        """
        Initialize MCPHelper.

        Args:
            tools_dir: Directory where tool Python files are stored
            configs_dir: Directory where tool YAML configs are stored
        """
        self.tools_dir = tools_dir
        self.configs_dir = configs_dir

    def create_tool_template(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Dict[str, Any]],
        return_type: str = "Dict[str, Any]",
        author: str = "Auto-generated",
        version: str = "1.0.0"
    ) -> str:
        """
        Generate a Python template for a new MCP tool.

        Args:
            name: Name of the tool (snake_case)
            description: Brief description of what the tool does
            parameters: Dictionary of parameter definitions
            return_type: Python type hint for return value
            author: Tool author name
            version: Tool version

        Returns:
            String containing the generated Python code
        """
        # Generate parameter list with type hints
        param_list = []
        for param_name, param_info in parameters.items():
            param_type = self._python_type_from_json_type(param_info.get("type", "string"))
            default = param_info.get("default")

            if default is not None:
                if isinstance(default, str):
                    param_list.append(f'{param_name}: {param_type} = "{default}"')
                else:
                    param_list.append(f'{param_name}: {param_type} = {default}')
            else:
                param_list.append(f'{param_name}: {param_type}')

        params_str = ", ".join(param_list)

        # Generate docstring
        docstring_params = []
        for param_name, param_info in parameters.items():
            docstring_params.append(
                f'        {param_name}: {param_info.get("description", "No description")}'
            )

        docstring = f'''"""
    {description}

    Args:
{chr(10).join(docstring_params)}

    Returns:
        Dictionary containing the result with status and data

    Author: {author}
    Version: {version}
    """'''

        # Generate template code
        template = f'''"""
MCP Tool: {name}
{description}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from typing import {return_type}


def {name}({params_str}) -> {return_type}:
    {docstring}
    try:
        # TODO: Implement your tool logic here
        result = {{
            "message": "Tool executed successfully",
            "parameters": {{
{self._generate_param_dict(parameters)}
            }}
        }}

        return {{
            "status": "success",
            "result": result
        }}

    except ValueError as e:
        return {{
            "status": "error",
            "error": f"Invalid parameter: {{str(e)}}"
        }}
    except Exception as e:
        return {{
            "status": "error",
            "error": str(e)
        }}


# Example usage
if __name__ == "__main__":
    # Test your tool
{self._generate_test_code(name, parameters)}
'''

        return template

    def create_config_template(
        self,
        tool_name: str,
        description: str = "",
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        version: str = "1.0.0"
    ) -> Dict[str, Any]:
        """
        Generate a YAML configuration template for a tool.

        Args:
            tool_name: Name of the tool
            description: Tool description
            parameters: Parameter definitions
            examples: List of example inputs/outputs
            version: Tool version

        Returns:
            Dictionary containing the configuration structure
        """
        parameters = parameters or {}
        examples = examples or []

        config = {
            "tool": {
                "name": tool_name,
                "description": description or f"MCP tool: {tool_name}",
                "version": version
            },
            "parameters": {
                "name_mappings": self._generate_name_mappings(parameters),
                "smart_defaults": self._generate_smart_defaults(parameters)
            },
            "examples": examples if examples else self._generate_example_templates(tool_name, parameters),
            "error_recovery": {
                "strategies": [
                    {
                        "error_pattern": "invalid.*parameter",
                        "recovery_action": "validate_and_sanitize",
                        "retry": True
                    },
                    {
                        "error_pattern": ".*not found.*",
                        "recovery_action": "use_fallback_value",
                        "retry": True
                    }
                ]
            },
            "optimization": {
                "enabled": True,
                "accuracy_metrics": {
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "parameter_correction_rate": 0.0,
                    "error_recovery_rate": 0.0
                },
                "last_updated": None
            }
        }

        return config

    def save_tool_file(self, tool_name: str, template_code: str) -> str:
        """
        Save tool template to a Python file.

        Args:
            tool_name: Name of the tool
            template_code: Generated Python code

        Returns:
            Path to the created file
        """
        filename = f"{tool_name}.py"
        filepath = os.path.join(self.tools_dir, filename)

        os.makedirs(self.tools_dir, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template_code)

        return filepath

    def save_config_file(self, tool_name: str, config: Dict[str, Any]) -> str:
        """
        Save configuration to a YAML file.

        Args:
            tool_name: Name of the tool
            config: Configuration dictionary

        Returns:
            Path to the created file
        """
        filename = f"{tool_name}.yaml"
        filepath = os.path.join(self.configs_dir, filename)

        os.makedirs(self.configs_dir, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return filepath

    def generate_tool_schema(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate JSON schema for tool registration.

        Args:
            name: Tool name
            description: Tool description
            parameters: Parameter definitions

        Returns:
            JSON schema dictionary
        """
        required_params = [
            param_name
            for param_name, param_info in parameters.items()
            if param_info.get("required", True) and "default" not in param_info
        ]

        schema = {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    param_name: {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", ""),
                        **({} if "default" not in param_info else {"default": param_info["default"]})
                    }
                    for param_name, param_info in parameters.items()
                },
                "required": required_params
            }
        }

        return schema

    def validate_tool_structure(self, tool_name: str) -> Dict[str, Any]:
        """
        Validate that a tool has all required components.

        Args:
            tool_name: Name of the tool to validate

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "components": {
                "python_file": False,
                "config_file": False,
                "schema_registered": False
            }
        }

        # Check Python file
        tool_file = os.path.join(self.tools_dir, f"{tool_name}.py")
        if os.path.exists(tool_file):
            results["components"]["python_file"] = True
        else:
            results["valid"] = False
            results["errors"].append(f"Python file not found: {tool_file}")

        # Check config file
        config_file = os.path.join(self.configs_dir, f"{tool_name}.yaml")
        if os.path.exists(config_file):
            results["components"]["config_file"] = True
        else:
            results["warnings"].append(f"Config file not found: {config_file} (optional but recommended)")

        return results

    # Private helper methods

    def _python_type_from_json_type(self, json_type: str) -> str:
        """Convert JSON schema type to Python type hint."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "List",
            "object": "Dict"
        }
        return type_map.get(json_type, "Any")

    def _generate_param_dict(self, parameters: Dict[str, Dict[str, Any]]) -> str:
        """Generate parameter dictionary for template."""
        lines = []
        for param_name in parameters.keys():
            lines.append(f'                "{param_name}": {param_name}')
        return ",\n".join(lines)

    def _generate_test_code(self, name: str, parameters: Dict[str, Dict[str, Any]]) -> str:
        """Generate test code for template."""
        test_params = []
        for param_name, param_info in parameters.items():
            default = param_info.get("default")
            if default is not None:
                if isinstance(default, str):
                    test_params.append(f'{param_name}="{default}"')
                else:
                    test_params.append(f'{param_name}={default}')
            else:
                # Use example values based on type
                param_type = param_info.get("type", "string")
                if param_type == "string":
                    test_params.append(f'{param_name}="test_value"')
                elif param_type == "integer":
                    test_params.append(f'{param_name}=42')
                elif param_type == "number":
                    test_params.append(f'{param_name}=3.14')
                elif param_type == "boolean":
                    test_params.append(f'{param_name}=True')

        params_str = ", ".join(test_params)
        return f'    result = {name}({params_str})\n    print(result)'

    def _generate_name_mappings(self, parameters: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Generate common parameter name variations."""
        mappings = {}
        for param_name in parameters.keys():
            # Add some common variations
            if param_name == "text":
                mappings.update({"message": "text", "content": "text", "input": "text"})
            elif param_name == "url":
                mappings.update({"link": "url", "address": "url"})
            elif param_name == "count":
                mappings.update({"number": "count", "num": "count", "quantity": "count"})
        return mappings

    def _generate_smart_defaults(self, parameters: Dict[str, Dict[str, Any]]) -> Dict[str, Dict]:
        """Generate smart defaults for parameters with default values."""
        smart_defaults = {}
        for param_name, param_info in parameters.items():
            if "default" in param_info:
                smart_defaults[param_name] = {
                    "strategy": "context_aware",
                    "default_value": param_info["default"],
                    "fallback_values": [param_info["default"]]
                }
        return smart_defaults

    def _generate_example_templates(
        self,
        tool_name: str,
        parameters: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate example templates for the configuration."""
        examples = []

        # Example 1: Basic usage with all required parameters
        input_params = {}
        for param_name, param_info in parameters.items():
            default = param_info.get("default")
            param_type = param_info.get("type", "string")

            if default is not None:
                input_params[param_name] = default
            elif param_type == "string":
                input_params[param_name] = "example_value"
            elif param_type == "integer":
                input_params[param_name] = 42
            elif param_type == "number":
                input_params[param_name] = 3.14
            elif param_type == "boolean":
                input_params[param_name] = True

        examples.append({
            "description": "Basic usage example",
            "input": {
                "raw_params": input_params
            },
            "expected_output": {
                "status": "success",
                "result": f"{tool_name} executed successfully"
            }
        })

        # Example 2: Minimal parameters (only required)
        minimal_params = {
            param_name: input_params[param_name]
            for param_name, param_info in parameters.items()
            if param_info.get("required", True) and "default" not in param_info
        }

        if len(minimal_params) < len(input_params):
            examples.append({
                "description": "Minimal parameters example",
                "input": {
                    "raw_params": minimal_params
                },
                "expected_output": {
                    "status": "success",
                    "result": f"{tool_name} executed with defaults"
                }
            })

        return examples


# Convenience functions for quick tool creation

def quick_create_tool(
    name: str,
    description: str,
    parameters: Dict[str, Dict[str, Any]],
    examples: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, str]:
    """
    Quickly create a new MCP tool with all necessary files.

    Args:
        name: Tool name (snake_case)
        description: Tool description
        parameters: Parameter definitions
        examples: Optional list of examples

    Returns:
        Dictionary with paths to created files
    """
    helper = MCPHelper()

    # Generate and save Python template
    template_code = helper.create_tool_template(name, description, parameters)
    tool_path = helper.save_tool_file(name, template_code)

    # Generate and save configuration
    config = helper.create_config_template(name, description, parameters, examples)
    config_path = helper.save_config_file(name, config)

    # Generate schema
    schema = helper.generate_tool_schema(name, description, parameters)

    return {
        "tool_file": tool_path,
        "config_file": config_path,
        "schema": schema,
        "status": "success",
        "message": f"Tool '{name}' created successfully! Remember to register it in server.py"
    }


def validate_tool(tool_name: str) -> Dict[str, Any]:
    """
    Validate a tool's structure and components.

    Args:
        tool_name: Name of the tool to validate

    Returns:
        Validation results
    """
    helper = MCPHelper()
    return helper.validate_tool_structure(tool_name)


# Example usage
if __name__ == "__main__":
    # Example: Create a new "sentiment_analysis" tool
    result = quick_create_tool(
        name="sentiment_analysis",
        description="Analyze the sentiment of a given text",
        parameters={
            "text": {
                "type": "string",
                "description": "The text to analyze",
                "required": True
            },
            "language": {
                "type": "string",
                "description": "Language of the text",
                "default": "en"
            },
            "detailed": {
                "type": "boolean",
                "description": "Return detailed analysis",
                "default": False
            }
        },
        examples=[
            {
                "description": "Positive sentiment example",
                "input": {
                    "raw_params": {
                        "text": "This is amazing!",
                        "language": "en"
                    }
                },
                "expected_output": {
                    "status": "success",
                    "result": {
                        "sentiment": "positive",
                        "score": 0.95
                    }
                }
            }
        ]
    )

    print("Tool creation result:")
    print(f"  Tool file: {result['tool_file']}")
    print(f"  Config file: {result['config_file']}")
    print(f"  Status: {result['status']}")
    print(f"  Message: {result['message']}")
    print("\nGenerated schema:")
    import json
    print(json.dumps(result['schema'], indent=2))
