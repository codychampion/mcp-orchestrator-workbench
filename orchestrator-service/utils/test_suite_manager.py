"""
MCP Test Suite Manager - LLM-driven test generation and execution
Generates test cases, runs them through AgentFlow, validates outputs
"""

import json
import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class TestSuiteManager:
    """Manages automated testing for MCP tools"""

    def __init__(self):
        self.test_suite_path = os.path.join(os.path.dirname(__file__), 'test_suites')
        os.makedirs(self.test_suite_path, exist_ok=True)

        self.github_token = os.getenv("GITHUB_TOKEN")
        self.llm_endpoint = "https://models.inference.ai.azure.com/chat/completions"

    async def generate_test_cases(self, tools: List[Dict[str, Any]], count: int = 5) -> List[Dict[str, Any]]:
        """
        Use LLM to generate test cases for tools.
        Each test case has: task, expected_output, tools_needed, success_criteria
        """
        test_cases = []

        for tool in tools[:min(len(tools), 10)]:  # Limit to prevent quota issues
            tool_name = tool.get('name')
            tool_description = tool.get('description', '')
            tool_schema = tool.get('inputSchema', {})

            # Generate test cases using LLM
            prompt = f"""Generate {count} realistic test cases for this MCP tool.

Tool: {tool_name}
Description: {tool_description}
Parameters: {json.dumps(tool_schema.get('properties', {}), indent=2)}

For each test case, provide:
1. task: A natural language task a user would ask
2. expected_output: What result we expect (be specific)
3. success_criteria: How to validate if the output is correct

Format as JSON array:
[
  {{
    "task": "Get weather in Paris",
    "expected_output": "Temperature and conditions for Paris",
    "success_criteria": "Response contains Paris and temperature value",
    "tool": "{tool_name}"
  }}
]

Generate diverse test cases covering edge cases, typical use, and error scenarios."""

            try:
                response = requests.post(
                    self.llm_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.github_token}"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=30
                )

                if response.ok:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]

                    # Extract JSON from response
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]

                    tool_tests = json.loads(content.strip())
                    test_cases.extend(tool_tests)

            except Exception as e:
                print(f"[TestGen] Failed to generate tests for {tool_name}: {e}")
                continue

        # Save generated test suite
        suite_id = f"suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        suite_path = os.path.join(self.test_suite_path, f"{suite_id}.json")

        test_suite = {
            "suite_id": suite_id,
            "generated_at": datetime.now().isoformat(),
            "test_count": len(test_cases),
            "tests": test_cases
        }

        with open(suite_path, 'w') as f:
            json.dump(test_suite, f, indent=2)

        print(f"[TestGen] Generated {len(test_cases)} test cases in {suite_id}")
        return test_cases

    async def run_test_suite(self, suite_id: str, agent_flow_url: str = "http://localhost:8100/agent-flow") -> Dict[str, Any]:
        """
        Execute a test suite through AgentFlow and collect results.
        Compares actual outputs against expected outputs.
        """
        # Load test suite
        suite_path = os.path.join(self.test_suite_path, f"{suite_id}.json")
        if not os.path.exists(suite_path):
            raise ValueError(f"Test suite {suite_id} not found")

        with open(suite_path, 'r') as f:
            test_suite = json.load(f)

        results = {
            "suite_id": suite_id,
            "started_at": datetime.now().isoformat(),
            "total_tests": len(test_suite["tests"]),
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "test_results": []
        }

        for idx, test_case in enumerate(test_suite["tests"]):
            print(f"[TestRun] Running test {idx + 1}/{results['total_tests']}: {test_case['task']}")

            test_result = await self._execute_test_case(test_case, agent_flow_url)
            results["test_results"].append(test_result)

            if test_result["status"] == "passed":
                results["passed"] += 1
            elif test_result["status"] == "failed":
                results["failed"] += 1
            else:
                results["errors"] += 1

        results["completed_at"] = datetime.now().isoformat()
        results["success_rate"] = (results["passed"] / results["total_tests"]) * 100

        # Save results
        results_path = os.path.join(self.test_suite_path, f"{suite_id}_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"[TestRun] Suite complete: {results['passed']}/{results['total_tests']} passed ({results['success_rate']:.1f}%)")
        return results

    async def _execute_test_case(self, test_case: Dict[str, Any], agent_flow_url: str) -> Dict[str, Any]:
        """Execute a single test case through AgentFlow"""
        result = {
            "task": test_case["task"],
            "expected_output": test_case["expected_output"],
            "tool": test_case.get("tool"),
            "status": "error",
            "actual_output": None,
            "execution_time_ms": 0,
            "validation_details": {}
        }

        start_time = datetime.now()

        try:
            # Start AgentFlow execution
            response = requests.post(
                f"{agent_flow_url}/start",
                json={
                    "agent_type": "executor",
                    "goal": test_case["task"],
                    "context": {}
                },
                timeout=60
            )

            if not response.ok:
                result["status"] = "error"
                result["validation_details"]["error"] = f"HTTP {response.status_code}"
                return result

            data = response.json()
            session_id = data.get("session_id")

            # Poll for completion (simplified - in production use WebSocket)
            import time
            max_wait = 30
            waited = 0

            while waited < max_wait:
                status_response = requests.get(f"{agent_flow_url}/{session_id}", timeout=10)
                if status_response.ok:
                    status_data = status_response.json()
                    if status_data.get("status") in ["completed", "failed", "error"]:
                        result["actual_output"] = status_data.get("result", "No output")
                        result["execution_log"] = status_data.get("execution_log", {})
                        break

                time.sleep(1)
                waited += 1

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result["execution_time_ms"] = execution_time

            # Validate output against expected
            validation = self._validate_output(
                result["actual_output"],
                test_case["expected_output"],
                test_case.get("success_criteria", "")
            )

            result["status"] = "passed" if validation["success"] else "failed"
            result["validation_details"] = validation

        except Exception as e:
            result["status"] = "error"
            result["validation_details"]["error"] = str(e)

        return result

    def _validate_output(self, actual: str, expected: str, criteria: str) -> Dict[str, Any]:
        """
        Validate actual output against expected output.
        Uses simple heuristics and optionally LLM for semantic validation.
        """
        validation = {
            "success": False,
            "confidence": 0.0,
            "details": []
        }

        if not actual:
            validation["details"].append("No output received")
            return validation

        actual_lower = str(actual).lower()
        expected_lower = str(expected).lower()

        # Simple keyword matching
        expected_keywords = [word for word in expected_lower.split() if len(word) > 3]
        matched_keywords = sum(1 for kw in expected_keywords if kw in actual_lower)

        if expected_keywords:
            keyword_match_rate = matched_keywords / len(expected_keywords)
            validation["confidence"] = keyword_match_rate
            validation["details"].append(f"Keyword match: {matched_keywords}/{len(expected_keywords)}")

            if keyword_match_rate >= 0.6:  # 60% keyword match
                validation["success"] = True

        # Check criteria if provided
        if criteria:
            criteria_met = all(
                term.strip().lower() in actual_lower
                for term in criteria.split(" and ")
            )
            validation["details"].append(f"Criteria met: {criteria_met}")

            if criteria_met:
                validation["success"] = True
                validation["confidence"] = max(validation["confidence"], 0.8)

        return validation

    def get_test_suites(self) -> List[Dict[str, Any]]:
        """List all available test suites"""
        suites = []
        for filename in os.listdir(self.test_suite_path):
            if filename.endswith('.json') and not filename.endswith('_results.json'):
                suite_path = os.path.join(self.test_suite_path, filename)
                try:
                    with open(suite_path, 'r') as f:
                        suite_data = json.load(f)
                        suites.append({
                            "suite_id": suite_data.get("suite_id"),
                            "generated_at": suite_data.get("generated_at"),
                            "test_count": suite_data.get("test_count"),
                            "has_results": os.path.exists(
                                os.path.join(self.test_suite_path, f"{suite_data.get('suite_id')}_results.json")
                            )
                        })
                except:
                    continue

        return sorted(suites, key=lambda x: x.get("generated_at", ""), reverse=True)

    def get_test_results(self, suite_id: str) -> Optional[Dict[str, Any]]:
        """Get results for a specific test suite"""
        results_path = os.path.join(self.test_suite_path, f"{suite_id}_results.json")
        if os.path.exists(results_path):
            with open(results_path, 'r') as f:
                return json.load(f)
        return None


# Singleton instance
_test_manager = None

def get_test_manager() -> TestSuiteManager:
    """Get or create test suite manager instance"""
    global _test_manager
    if _test_manager is None:
        _test_manager = TestSuiteManager()
    return _test_manager
