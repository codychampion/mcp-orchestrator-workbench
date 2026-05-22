"""
Remote Configuration Manager for Orchestrator
Fetches tool configs from MCP server instead of storing locally
"""

import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime


class RemoteConfigManager:
    """Fetches and updates tool configurations from MCP server"""

    def __init__(self, mcp_server_url: str = None):
        # Config API runs on port 8001, MCP SSE runs on port 8000
        self.mcp_server_url = mcp_server_url or os.getenv("MCP_CONFIG_URL", "http://mcp-server:8001")
        print(f"[Remote Config] MCP Config API URL: {self.mcp_server_url}")

    async def load_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Load configuration for a specific tool from MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_server_url}/configs/{tool_name}",
                    timeout=5.0
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"[Remote Config] Loaded config for {tool_name}")
                    return data.get("config")
                elif response.status_code == 404:
                    print(f"[Remote Config] No config found for {tool_name}")
                    return None
                else:
                    print(f"[Remote Config] Error loading {tool_name}: {response.status_code}")
                    return None

        except Exception as e:
            print(f"[Remote Config] Failed to load config for {tool_name}: {e}")
            return None

    async def save_tool_config(self, tool_name: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a specific tool to MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.mcp_server_url}/configs/{tool_name}",
                    json={"config": config},
                    timeout=5.0
                )

                if response.status_code == 200:
                    print(f"[Remote Config] Saved config for {tool_name}")
                    return True
                else:
                    print(f"[Remote Config] Error saving {tool_name}: {response.status_code}")
                    return False

        except Exception as e:
            print(f"[Remote Config] Failed to save config for {tool_name}: {e}")
            return False

    async def load_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all tool configurations from MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_server_url}/configs",
                    timeout=5.0
                )

                if response.status_code == 200:
                    data = response.json()
                    configs = data.get("configs", {})
                    print(f"[Remote Config] Loaded {len(configs)} tool configs")
                    return configs
                else:
                    print(f"[Remote Config] Error loading all configs: {response.status_code}")
                    return {}

        except Exception as e:
            print(f"[Remote Config] Failed to load all configs: {e}")
            return {}

    def get_parameter_mappings(self, tool_name: str) -> Dict[str, str]:
        """Get parameter name mappings for a tool (sync version)"""
        import asyncio
        try:
            config = asyncio.run(self.load_tool_config(tool_name))
            if config and "parameters" in config and "name_mappings" in config["parameters"]:
                return config["parameters"]["name_mappings"]
            return {}
        except Exception as e:
            print(f"[Remote Config] Error getting mappings for {tool_name}: {e}")
            return {}

    async def add_parameter_mapping(self, tool_name: str, wrong_name: str, correct_name: str) -> bool:
        """Add a learned parameter name mapping via MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/configs/{tool_name}/mappings",
                    json={
                        "wrong_name": wrong_name,
                        "correct_name": correct_name
                    },
                    timeout=5.0
                )

                if response.status_code == 200:
                    print(f"[Remote Config] Added mapping {wrong_name} → {correct_name} for {tool_name}")
                    return True
                else:
                    print(f"[Remote Config] Error adding mapping: {response.status_code}")
                    return False

        except Exception as e:
            print(f"[Remote Config] Failed to add mapping: {e}")
            return False

    async def update_tool_metrics(self, tool_name: str, success: bool, corrected: bool = False) -> bool:
        """Update optimization metrics for a tool via MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/configs/{tool_name}/metrics",
                    json={
                        "success": success,
                        "corrected": corrected
                    },
                    timeout=5.0
                )

                if response.status_code == 200:
                    print(f"[Remote Config] Updated metrics for {tool_name}")
                    return True
                else:
                    print(f"[Remote Config] Error updating metrics: {response.status_code}")
                    return False

        except Exception as e:
            print(f"[Remote Config] Failed to update metrics: {e}")
            return False

    async def add_example(self, tool_name: str, example: Dict[str, Any]) -> bool:
        """Add a training example to tool config via MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/configs/{tool_name}/examples",
                    json={"example": example},
                    timeout=5.0
                )

                if response.status_code == 200:
                    print(f"[Remote Config] Added example for {tool_name}")
                    return True
                else:
                    print(f"[Remote Config] Error adding example: {response.status_code}")
                    return False

        except Exception as e:
            print(f"[Remote Config] Failed to add example: {e}")
            return False

    async def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of all optimizations from MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_server_url}/configs/summary/optimizations",
                    timeout=5.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("summary", {})
                else:
                    print(f"[Remote Config] Error getting summary: {response.status_code}")
                    return {}

        except Exception as e:
            print(f"[Remote Config] Failed to get summary: {e}")
            return {}

    def initialize_configs_from_mcp_tools(self, mcp_tools) -> int:
        """This is a no-op for remote config - MCP server manages its own configs"""
        print("[Remote Config] Skipping config initialization - MCP server manages configs")
        return 0

    async def update_orchestrator_metrics(self, metric_type: str, metrics: Dict[str, Any]) -> bool:
        """Update orchestrator-wide metrics (stored locally)"""
        # Orchestrator metrics stay local
        print(f"[Remote Config] Orchestrator metrics stored locally: {metric_type}")
        return True

    def enhance_parameters(self, tool_name: str, params: Dict[str, Any], context: list) -> Dict[str, Any]:
        """Apply parameter enhancements based on learned mappings (sync wrapper)"""
        import asyncio
        try:
            config = asyncio.run(self.load_tool_config(tool_name))
            if not config:
                return params

            # Apply parameter name mappings
            name_mappings = config.get('parameters', {}).get('name_mappings', {})
            enhanced = params.copy()

            for wrong_name, correct_name in name_mappings.items():
                if wrong_name in enhanced and correct_name not in enhanced:
                    enhanced[correct_name] = enhanced.pop(wrong_name)
                    print(f"[Remote Config] Mapped {wrong_name} → {correct_name} for {tool_name}")

            # Apply smart defaults
            smart_defaults = config.get('parameters', {}).get('smart_defaults', {})
            schema = config.get('parameters', {}).get('schema', {})

            for param_name, param_info in schema.items():
                if param_info.get('required') and param_name not in enhanced:
                    default_config = smart_defaults.get(param_name, {})
                    if 'fallback' in default_config and default_config['fallback'] is not None:
                        enhanced[param_name] = default_config['fallback']
                        print(f"[Remote Config] Applied default {param_name} = {default_config['fallback']} for {tool_name}")

            # Track if we made corrections
            if enhanced != params:
                asyncio.run(self.update_tool_metrics(tool_name, success=True, corrected=True))

            return enhanced

        except Exception as e:
            print(f"[Remote Config] Error enhancing parameters for {tool_name}: {e}")
            return params

    def recover_from_error(self, tool_name: str, params: Dict[str, Any], error: str, context: list) -> Dict[str, Any]:
        """Attempt to recover from error using error recovery strategies (sync wrapper)"""
        import asyncio
        try:
            config = asyncio.run(self.load_tool_config(tool_name))
            if not config:
                return params

            error_strategies = config.get('error_recovery', {}).get('strategies', [])
            recovered = params.copy()

            for strategy in error_strategies:
                error_pattern = strategy.get('error_pattern', '')

                # Check if error matches this pattern
                if error_pattern.lower() in error.lower():
                    action = strategy.get('recovery_action', '')

                    if action == 'use_default':
                        # Use default value from strategy
                        default_value = strategy.get('default_value')
                        if default_value:
                            # Try to infer which parameter failed
                            for param_name in params.keys():
                                if param_name.lower() in error.lower():
                                    recovered[param_name] = default_value
                                    print(f"[Remote Config] Recovery: Set {param_name} = {default_value} for {tool_name}")
                                    break

                    elif action == 'extract_from_context':
                        # Try to extract from context
                        context_hints = strategy.get('context_hints', [])
                        for hint in context_hints:
                            for ctx_item in context:
                                if isinstance(ctx_item, dict) and hint in str(ctx_item).lower():
                                    # Simple extraction - could be smarter
                                    print(f"[Remote Config] Recovery: Found context match for {hint}")

                    elif action == 'suggest_alternatives':
                        # Log the suggestion
                        print(f"[Remote Config] Recovery suggestion: {strategy.get('suggestion_strategy', 'none')}")

            # Track recovery attempt
            if recovered != params:
                asyncio.run(self.update_tool_metrics(tool_name, success=False, corrected=True))

            return recovered

        except Exception as e:
            print(f"[Remote Config] Error recovering from error for {tool_name}: {e}")
            return params

    def export_optimization_summary(self) -> Dict[str, Any]:
        """Export summary from remote MCP server"""
        import asyncio
        try:
            return asyncio.run(self.get_optimization_summary())
        except Exception as e:
            print(f"[Remote Config] Error exporting summary: {e}")
            return {"tools": {}, "orchestrator": {}}


# Global config manager instance
_remote_config_manager = None

def get_remote_config_manager() -> RemoteConfigManager:
    """Get singleton remote config manager instance"""
    global _remote_config_manager
    if _remote_config_manager is None:
        _remote_config_manager = RemoteConfigManager()
    return _remote_config_manager
