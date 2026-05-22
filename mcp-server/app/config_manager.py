"""
Configuration Manager for MCP Tools
Loads and manages YAML configs for each tool
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class MCPConfigManager:
    """Manages YAML configurations for MCP tools"""

    def __init__(self, config_base_path: str = None):
        if config_base_path is None:
            # Default to configs directory relative to this file
            self.base_path = Path(__file__).parent / "configs" / "tools"
        else:
            self.base_path = Path(config_base_path)

        # Ensure directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        print(f"[MCP Config] Config path: {self.base_path}")

    def load_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Load configuration for a specific tool"""
        config_file = self.base_path / f"{tool_name}.yaml"

        if not config_file.exists():
            print(f"[MCP Config] No config file found for tool: {tool_name}")
            return None

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"[MCP Config] Loaded config for {tool_name}")
            return config
        except Exception as e:
            print(f"[MCP Config] Error loading config for {tool_name}: {e}")
            return None

    def save_tool_config(self, tool_name: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a specific tool"""
        config_file = self.base_path / f"{tool_name}.yaml"

        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print(f"[MCP Config] Saved config for {tool_name}")
            return True
        except Exception as e:
            print(f"[MCP Config] Error saving config for {tool_name}: {e}")
            return False

    def load_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all tool configurations"""
        configs = {}

        for config_file in self.base_path.glob("*.yaml"):
            # Skip template
            if config_file.name.startswith("_"):
                continue

            tool_name = config_file.stem
            config = self.load_tool_config(tool_name)
            if config:
                configs[tool_name] = config

        print(f"[MCP Config] Loaded {len(configs)} tool configs")
        return configs

    def get_parameter_mappings(self, tool_name: str) -> Dict[str, str]:
        """Get parameter name mappings for a tool"""
        config = self.load_tool_config(tool_name)
        if config and "parameters" in config and "name_mappings" in config["parameters"]:
            return config["parameters"]["name_mappings"]
        return {}

    def add_parameter_mapping(self, tool_name: str, wrong_name: str, correct_name: str) -> bool:
        """Add a learned parameter name mapping"""
        config = self.load_tool_config(tool_name)
        if not config:
            # Create default config if it doesn't exist
            config = self._create_default_config(tool_name)

        if "parameters" not in config:
            config["parameters"] = {}
        if "name_mappings" not in config["parameters"]:
            config["parameters"]["name_mappings"] = {}

        config["parameters"]["name_mappings"][wrong_name] = correct_name

        # Update optimization metadata
        if "optimization" not in config:
            config["optimization"] = {}
        config["optimization"]["last_updated"] = datetime.now().isoformat()

        return self.save_tool_config(tool_name, config)

    def update_tool_metrics(self, tool_name: str, success: bool, corrected: bool = False) -> bool:
        """Update optimization metrics for a tool"""
        config = self.load_tool_config(tool_name)
        if not config:
            config = self._create_default_config(tool_name)

        if "optimization" not in config:
            config["optimization"] = {}
        if "accuracy_metrics" not in config["optimization"]:
            config["optimization"]["accuracy_metrics"] = {}

        metrics = config["optimization"]["accuracy_metrics"]

        if success:
            metrics["successful_calls"] = metrics.get("successful_calls", 0) + 1
        else:
            metrics["failed_calls"] = metrics.get("failed_calls", 0) + 1

        if corrected:
            total_calls = metrics.get("successful_calls", 0) + metrics.get("failed_calls", 0)
            if total_calls > 0:
                correction_count = metrics.get("parameter_correction_rate", 0.0) * total_calls
                metrics["parameter_correction_rate"] = (correction_count + 1) / (total_calls + 1)

        config["optimization"]["last_updated"] = datetime.now().isoformat()

        return self.save_tool_config(tool_name, config)

    def add_example(self, tool_name: str, example: Dict[str, Any]) -> bool:
        """Add a training example to tool config"""
        config = self.load_tool_config(tool_name)
        if not config:
            config = self._create_default_config(tool_name)

        if "examples" not in config:
            config["examples"] = []

        config["examples"].append(example)

        # Keep only last 50 examples
        config["examples"] = config["examples"][-50:]

        config["optimization"]["last_updated"] = datetime.now().isoformat()

        return self.save_tool_config(tool_name, config)

    def _create_default_config(self, tool_name: str) -> Dict[str, Any]:
        """Create a default configuration for a tool"""
        return {
            "tool": {
                "name": tool_name,
                "description": "",
                "version": "1.0",
                "category": "general"
            },
            "parameters": {
                "schema": {},
                "name_mappings": {},
                "smart_defaults": {}
            },
            "examples": [],
            "error_recovery": {
                "strategies": []
            },
            "optimization": {
                "last_updated": None,
                "optimization_count": 0,
                "accuracy_metrics": {
                    "parameter_correction_rate": 0.0,
                    "error_recovery_rate": 0.0,
                    "successful_calls": 0,
                    "failed_calls": 0
                },
                "learned_patterns": []
            }
        }

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of all optimizations"""
        summary = {"tools": {}}

        for tool_name, config in self.load_all_configs().items():
            opt = config.get("optimization", {})
            summary["tools"][tool_name] = {
                "last_updated": opt.get("last_updated"),
                "optimization_count": opt.get("optimization_count", 0),
                "metrics": opt.get("accuracy_metrics", {}),
                "mappings_count": len(config.get("parameters", {}).get("name_mappings", {})),
                "examples_count": len(config.get("examples", []))
            }

        return summary


# Global config manager instance
_config_manager = None

def get_config_manager() -> MCPConfigManager:
    """Get singleton config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MCPConfigManager()
    return _config_manager
