"""
Configuration Manager for MCP Tools and Orchestrator
Handles reading and writing YAML configs that are optimized by DSPy
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

class ConfigManager:
    """Manages YAML configurations for tools and orchestrator"""

    def __init__(self, config_base_path: str = None):
        if config_base_path is None:
            # Default to configs directory relative to this file
            self.base_path = Path(__file__).parent.parent / "configs"
        else:
            self.base_path = Path(config_base_path)

        self.tools_path = self.base_path / "tools"
        self.orchestrator_path = self.base_path / "orchestrator"

        # Create directories if they don't exist
        self.tools_path.mkdir(parents=True, exist_ok=True)
        self.orchestrator_path.mkdir(parents=True, exist_ok=True)

    # Tool Configuration Methods

    def load_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Load configuration for a specific tool"""
        config_file = self.tools_path / f"{tool_name}.yaml"

        if not config_file.exists():
            print(f"[CONFIG] No config file found for tool: {tool_name}")
            return None

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"[CONFIG] Loaded config for {tool_name}")
            return config
        except Exception as e:
            print(f"[CONFIG] Error loading config for {tool_name}: {e}")
            return None

    def save_tool_config(self, tool_name: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a specific tool"""
        config_file = self.tools_path / f"{tool_name}.yaml"

        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print(f"[CONFIG] Saved config for {tool_name}")
            return True
        except Exception as e:
            print(f"[CONFIG] Error saving config for {tool_name}: {e}")
            return False

    def load_all_tool_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all tool configurations"""
        configs = {}

        for config_file in self.tools_path.glob("*.yaml"):
            # Skip template
            if config_file.name.startswith("_"):
                continue

            tool_name = config_file.stem
            config = self.load_tool_config(tool_name)
            if config:
                configs[tool_name] = config

        print(f"[CONFIG] Loaded {len(configs)} tool configs")
        return configs

    def create_tool_config_from_schema(self, tool_name: str, tool_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tool config from MCP tool schema"""
        config = {
            "tool": {
                "name": tool_name,
                "description": tool_schema.get("description", ""),
                "version": "1.0",
                "category": "general"
            },
            "parameters": {
                "schema": tool_schema.get("params_schema", {}),
                "name_mappings": {},
                "smart_defaults": {}
            },
            "examples": [],
            "error_recovery": {
                "strategies": []
            },
            "optimization": {
                "last_optimized": None,
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

        return config

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
            return False

        if "parameters" not in config:
            config["parameters"] = {}
        if "name_mappings" not in config["parameters"]:
            config["parameters"]["name_mappings"] = {}

        config["parameters"]["name_mappings"][wrong_name] = correct_name
        return self.save_tool_config(tool_name, config)

    def update_tool_metrics(self, tool_name: str, success: bool, corrected: bool = False) -> bool:
        """Update optimization metrics for a tool"""
        config = self.load_tool_config(tool_name)
        if not config:
            return False

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

        return self.save_tool_config(tool_name, config)

    # Orchestrator Configuration Methods

    def load_orchestrator_config(self) -> Dict[str, Any]:
        """Load orchestrator optimizer configuration"""
        config_file = self.orchestrator_path / "optimizer_config.yaml"

        if not config_file.exists():
            print("[CONFIG] No orchestrator config found, using defaults")
            return self._get_default_orchestrator_config()

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            print("[CONFIG] Loaded orchestrator config")
            return config
        except Exception as e:
            print(f"[CONFIG] Error loading orchestrator config: {e}")
            return self._get_default_orchestrator_config()

    def save_orchestrator_config(self, config: Dict[str, Any]) -> bool:
        """Save orchestrator optimizer configuration"""
        config_file = self.orchestrator_path / "optimizer_config.yaml"

        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print("[CONFIG] Saved orchestrator config")
            return True
        except Exception as e:
            print(f"[CONFIG] Error saving orchestrator config: {e}")
            return False

    def update_orchestrator_metrics(self, metric_type: str, metrics: Dict[str, Any]) -> bool:
        """Update optimization metrics in orchestrator config"""
        config = self.load_orchestrator_config()

        if "optimization" not in config:
            config["optimization"] = {}
        if "current_metrics" not in config["optimization"]:
            config["optimization"]["current_metrics"] = {}

        config["optimization"]["current_metrics"][metric_type] = metrics
        config["optimization"]["last_full_optimization"] = datetime.now().isoformat()

        return self.save_orchestrator_config(config)

    def add_learned_prompt(self, prompt_type: str, prompt_text: str) -> bool:
        """Save an optimized prompt learned by DSPy"""
        config = self.load_orchestrator_config()

        if "learned_prompts" not in config:
            config["learned_prompts"] = {}

        config["learned_prompts"][prompt_type] = prompt_text
        return self.save_orchestrator_config(config)

    def get_learned_prompt(self, prompt_type: str) -> Optional[str]:
        """Get an optimized prompt"""
        config = self.load_orchestrator_config()
        return config.get("learned_prompts", {}).get(prompt_type)

    def _get_default_orchestrator_config(self) -> Dict[str, Any]:
        """Get default orchestrator configuration"""
        return {
            "orchestrator": {
                "name": "MCP Orchestrator",
                "version": "1.0"
            },
            "optimization": {
                "current_metrics": {}
            },
            "learned_prompts": {}
        }

    # Bulk Operations

    def initialize_configs_from_mcp_tools(self, mcp_tools: List[Dict[str, Any]]) -> int:
        """Initialize tool configs for MCP tools that don't have configs yet"""
        created_count = 0

        for tool in mcp_tools:
            tool_name = tool.get("name")
            if not tool_name:
                continue

            # Check if config already exists
            if self.load_tool_config(tool_name) is not None:
                continue

            # Create new config from schema
            config = self.create_tool_config_from_schema(tool_name, tool)
            if self.save_tool_config(tool_name, config):
                created_count += 1

        print(f"[CONFIG] Initialized {created_count} new tool configs")
        return created_count

    def export_optimization_summary(self) -> Dict[str, Any]:
        """Export summary of all optimizations"""
        summary = {
            "tools": {},
            "orchestrator": {}
        }

        # Tool summaries
        for tool_name, config in self.load_all_tool_configs().items():
            opt = config.get("optimization", {})
            summary["tools"][tool_name] = {
                "last_optimized": opt.get("last_optimized"),
                "optimization_count": opt.get("optimization_count", 0),
                "metrics": opt.get("accuracy_metrics", {})
            }

        # Orchestrator summary
        orch_config = self.load_orchestrator_config()
        summary["orchestrator"] = orch_config.get("optimization", {}).get("current_metrics", {})

        return summary


# Global config manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get singleton config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
