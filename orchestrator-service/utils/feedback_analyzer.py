"""
Feedback Analyzer - Learns from user feedback to optimize MCP configs
Analyzes parameter errors, tool selection mistakes, and updates YAML configs
"""

import json
import os
import yaml
import requests
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime


class FeedbackAnalyzer:
    """Analyzes user feedback and updates MCP tool configurations"""

    def __init__(self):
        self.logging_service_url = os.getenv("LOGGING_SERVICE_URL", "http://logging-service:8200")
        self.mcp_config_url = os.getenv("MCP_CONFIG_URL", "http://mcp-server:8001")

    async def analyze_and_update_configs(self) -> Dict[str, Any]:
        """
        Main workflow:
        1. Fetch feedback from logging service
        2. Analyze patterns (parameter errors, tool mistakes)
        3. Update YAML configs based on patterns
        4. Return summary of changes
        """
        print("[FeedbackAnalyzer] Starting config optimization...")

        # Fetch feedback data
        feedback_data = await self._fetch_feedback()

        if not feedback_data or len(feedback_data) < 5:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 5 examples, found {len(feedback_data)}",
                "examples_analyzed": len(feedback_data)
            }

        # Analyze patterns
        analysis = self._analyze_patterns(feedback_data)

        # Generate config updates
        config_updates = self._generate_config_updates(analysis)

        # Apply updates to MCP server
        applied_updates = await self._apply_config_updates(config_updates)

        result = {
            "status": "success",
            "examples_analyzed": len(feedback_data),
            "patterns_found": len(analysis["patterns"]),
            "configs_updated": len(applied_updates),
            "updates": applied_updates,
            "analysis_summary": {
                "parameter_errors": analysis["parameter_errors"],
                "tool_selection_errors": analysis["tool_selection_errors"],
                "common_corrections": analysis["common_corrections"]
            },
            "timestamp": datetime.now().isoformat()
        }

        print(f"[FeedbackAnalyzer] Updated {len(applied_updates)} configs based on {len(feedback_data)} examples")
        return result

    async def _fetch_feedback(self) -> List[Dict[str, Any]]:
        """Fetch user feedback from logging service"""
        try:
            # Get LLM call logs (contains tool usage and errors)
            response = requests.get(
                f"{self.logging_service_url}/logs/llm",
                params={"limit": 200},
                timeout=10
            )

            if response.ok:
                data = response.json()
                return data.get("logs", [])

        except Exception as e:
            print(f"[FeedbackAnalyzer] Failed to fetch feedback: {e}")

        return []

    def _analyze_patterns(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze feedback to identify patterns:
        - Parameter name mistakes (e.g., "place" vs "location")
        - Missing required parameters
        - Tool selection errors
        - Common corrections
        """
        analysis = {
            "parameter_errors": defaultdict(list),
            "tool_selection_errors": defaultdict(int),
            "common_corrections": defaultdict(dict),
            "patterns": []
        }

        for log in feedback_data:
            prompt = log.get("prompt", "")
            response = log.get("response", "")
            metadata = log.get("metadata")

            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            # Ensure metadata is always a dict
            if metadata is None:
                metadata = {}

            # Look for parameter error patterns
            if "error" in response.lower() or "failed" in response.lower():
                # Extract tool name and error details
                if "parameter" in response.lower() or "required" in response.lower():
                    tool_name = self._extract_tool_name(prompt, response)
                    if tool_name:
                        analysis["parameter_errors"][tool_name].append({
                            "prompt": prompt[:200],
                            "error": response[:200],
                            "timestamp": log.get("timestamp")
                        })

            # Look for corrections in retry attempts
            if metadata.get("retry_count", 0) > 0:
                tool_name = metadata.get("tool_name")
                if tool_name:
                    prev_params = metadata.get("previous_params", {})
                    corrected_params = metadata.get("corrected_params", {})

                    if prev_params and corrected_params:
                        # Find what changed
                        for key in corrected_params:
                            if key not in prev_params:
                                # New parameter added
                                if tool_name not in analysis["common_corrections"]:
                                    analysis["common_corrections"][tool_name] = {}

                                correction_key = f"add_{key}"
                                if correction_key not in analysis["common_corrections"][tool_name]:
                                    analysis["common_corrections"][tool_name][correction_key] = {
                                        "count": 0,
                                        "examples": []
                                    }

                                analysis["common_corrections"][tool_name][correction_key]["count"] += 1
                                analysis["common_corrections"][tool_name][correction_key]["examples"].append({
                                    "before": prev_params,
                                    "after": corrected_params
                                })

                            elif prev_params.get(key) != corrected_params[key]:
                                # Parameter value changed - might indicate mapping issue
                                # E.g., "place" -> "location"
                                pass

        # Identify strong patterns (corrections that happen frequently)
        for tool_name, corrections in analysis["common_corrections"].items():
            for correction_type, data in corrections.items():
                if data["count"] >= 2:  # Pattern if happens 2+ times
                    analysis["patterns"].append({
                        "tool": tool_name,
                        "type": correction_type,
                        "frequency": data["count"],
                        "confidence": min(data["count"] / 10.0, 1.0),  # Max 1.0 at 10 occurrences
                        "examples": data["examples"][:3]  # Keep top 3
                    })

        return analysis

    def _extract_tool_name(self, prompt: str, response: str) -> Optional[str]:
        """Extract tool name from prompt or error message"""
        # Simple extraction - look for common patterns
        text = prompt + " " + response

        # Look for tool name patterns
        if "tool:" in text.lower():
            parts = text.lower().split("tool:")
            if len(parts) > 1:
                tool_part = parts[1].split()[0].strip("' \"")
                return tool_part

        return None

    def _generate_config_updates(self, analysis: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Generate YAML config updates based on analysis patterns.
        Returns: {tool_name: {yaml_updates}}
        """
        config_updates = {}

        for pattern in analysis["patterns"]:
            tool_name = pattern["tool"]
            correction_type = pattern["type"]
            confidence = pattern["confidence"]

            # Only apply high-confidence patterns
            if confidence < 0.3:
                continue

            if tool_name not in config_updates:
                config_updates[tool_name] = {
                    "parameter_mappings": {},
                    "default_values": {},
                    "confidence": confidence
                }

            # Parse correction type
            if correction_type.startswith("add_"):
                param_name = correction_type.replace("add_", "")

                # Analyze examples to determine if it's a mapping or default
                examples = pattern["examples"]
                if examples:
                    # Look at what value is commonly used
                    common_values = defaultdict(int)
                    for ex in examples:
                        value = ex["after"].get(param_name)
                        if value:
                            common_values[str(value)] += 1

                    if common_values:
                        most_common = max(common_values.items(), key=lambda x: x[1])
                        config_updates[tool_name]["default_values"][param_name] = most_common[0]

        return config_updates

    async def _apply_config_updates(self, config_updates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply config updates to MCP server's YAML configs.
        Returns list of successfully applied updates.
        """
        applied_updates = []

        for tool_name, updates in config_updates.items():
            try:
                # Get current config
                response = requests.get(f"{self.mcp_config_url}/configs/{tool_name}", timeout=5)

                if response.ok:
                    current_config = response.json().get("config", {})
                else:
                    current_config = {}

                # Merge updates
                updated_config = dict(current_config)

                if "parameter_mappings" in updates and updates["parameter_mappings"]:
                    if "parameter_mappings" not in updated_config:
                        updated_config["parameter_mappings"] = {}
                    updated_config["parameter_mappings"].update(updates["parameter_mappings"])

                if "default_values" in updates and updates["default_values"]:
                    if "default_values" not in updated_config:
                        updated_config["default_values"] = {}
                    updated_config["default_values"].update(updates["default_values"])

                # Update config on MCP server
                update_response = requests.post(
                    f"{self.mcp_config_url}/configs/{tool_name}",
                    json={"config": updated_config},
                    timeout=5
                )

                if update_response.ok:
                    applied_updates.append({
                        "tool": tool_name,
                        "changes": updates,
                        "confidence": updates.get("confidence", 0.5)
                    })
                    print(f"[FeedbackAnalyzer] Updated config for {tool_name}")

            except Exception as e:
                print(f"[FeedbackAnalyzer] Failed to update {tool_name}: {e}")
                continue

        return applied_updates


# Singleton instance
_analyzer = None

def get_feedback_analyzer() -> FeedbackAnalyzer:
    """Get or create feedback analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = FeedbackAnalyzer()
    return _analyzer
