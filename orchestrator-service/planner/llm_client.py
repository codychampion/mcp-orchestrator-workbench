# Standard LLM interface supporting multiple providers
import os
import requests
import json
import time
from datetime import datetime

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "github")
LOGGING_SERVICE_URL = os.getenv("LOGGING_SERVICE_URL", "http://logging-service:8200")

def _log_llm_call(messages, response, duration_ms, status, error=None, tokens_used=None, model=None, session_id=None, user_query=None):
    """Send LLM call details to logging service (non-blocking)"""
    try:
        log_payload = {
            "service": "orchestrator",
            "model": model or "unknown",
            "prompt": json.dumps(messages),
            "response": response if status == "success" else None,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "status": status,
            "error": error,
            "session_id": session_id,
            "user_query": user_query
        }

        # Don't fail the LLM call if logging fails
        requests.post(
            f"{LOGGING_SERVICE_URL}/logs/llm",
            json=log_payload,
            timeout=2  # Short timeout to not block execution
        )
    except Exception as log_error:
        # Log to console but don't fail
        print(f"[LLM] Warning: Failed to send log to logging service: {log_error}")

def call_llm(messages: list, max_tokens: int = 1000) -> str:
    """Standard LLM interface that works with any provider"""
    start_time = time.time()
    payload = {"messages": messages, "max_tokens": max_tokens}
    response = None
    error_msg = None
    status = "success"

    try:
        if LLM_PROVIDER == "github":
            response = _call_github(payload)
        elif LLM_PROVIDER == "azure":
            response = _call_azure(payload)
        else:
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

        duration_ms = (time.time() - start_time) * 1000

        # Log successful call
        _log_llm_call(
            messages=messages,
            response=response,
            duration_ms=duration_ms,
            status="success",
            model=f"{LLM_PROVIDER}-gpt-4o-mini"
        )

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)
        status = "error"

        # Log failed call
        _log_llm_call(
            messages=messages,
            response=None,
            duration_ms=duration_ms,
            status="error",
            error=error_msg,
            model=f"{LLM_PROVIDER}-gpt-4o-mini"
        )

        # Re-raise the original error
        raise

def _call_github(payload: dict) -> str:
    """Call GitHub models using direct HTTP requests with timeout"""
    endpoint = "https://models.inference.ai.azure.com/chat/completions"
    model_name = "gpt-4o-mini"
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is required. Please set it in your .env file.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    request_payload = {
        "model": model_name,
        "messages": payload.get("messages", []),
        "temperature": 0.7,
        "max_tokens": payload.get("max_tokens", 1000)
    }

    print(f"[LLM] Calling GitHub API with {len(request_payload['messages'])} messages")

    try:
        # Use requests with 30 second timeout
        response = requests.post(
            endpoint,
            headers=headers,
            json=request_payload,
            timeout=30
        )

        print(f"[LLM] Received response (status {response.status_code})")

        if response.status_code == 401:
            raise RuntimeError("GitHub token is invalid or expired. Please check your GITHUB_TOKEN.")
        elif response.status_code == 403:
            raise RuntimeError("GitHub API access forbidden. You may have exceeded rate limits or your token lacks permissions.")
        elif response.status_code == 429:
            raise RuntimeError("GitHub API rate limit exceeded. Please wait a few minutes or check your token's rate limit status.")
        elif response.status_code != 200:
            error_detail = response.text[:200] if response.text else "No error details"
            raise RuntimeError(f"GitHub API error (status {response.status_code}): {error_detail}")

        result_data = response.json()
        content = result_data["choices"][0]["message"]["content"]
        print(f"[LLM] Successfully received response")
        return content

    except requests.exceptions.Timeout:
        print(f"[LLM ERROR] Request timed out after 30 seconds")
        raise RuntimeError("GitHub API request timed out after 30 seconds. The API may be experiencing issues or your token may have rate limits.")

    except requests.exceptions.RequestException as e:
        print(f"[LLM ERROR] Request error: {e}")
        raise RuntimeError(f"Failed to connect to GitHub API: {str(e)}")

    except KeyError as e:
        print(f"[LLM ERROR] Unexpected response format: {e}")
        raise RuntimeError(f"GitHub API returned unexpected response format")

    except Exception as e:
        print(f"[LLM ERROR] Unexpected error: {e}")
        raise RuntimeError(f"Failed to call GitHub API: {str(e)}")

def _call_azure(payload: dict) -> str:
    """Call Azure AI Foundry (not Azure OpenAI)"""
    endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    api_key = os.getenv("AZURE_AI_FOUNDRY_KEY")
    model_name = os.getenv("AZURE_AI_FOUNDRY_MODEL", "gpt-4o-mini")

    if not endpoint or not api_key:
        raise RuntimeError("Azure AI Foundry config missing: AZURE_AI_FOUNDRY_ENDPOINT and AZURE_AI_FOUNDRY_KEY required")

    # Azure AI Foundry uses a different URL pattern than Azure OpenAI
    url = f"{endpoint}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Prepare payload for Azure AI Foundry
    foundry_payload = payload.copy()
    foundry_payload["model"] = model_name

    resp = requests.post(url, headers=headers, json=foundry_payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    return result["choices"][0]["message"]["content"]


def generate_plan_with_llm(tool_metadata, user_goal, chat_history=None):
    # Create a simple prompt for better LLM understanding
    tool_names = [t["name"] for t in tool_metadata]

    # Create tool schema summary for better parameter generation
    tool_schemas = {}
    for tool in tool_metadata:
        if tool.get("params_schema"):
            schema = tool["params_schema"]
            required = schema.get("required", [])
            properties = schema.get("properties", {})
            tool_schemas[tool["name"]] = {
                "required": required,
                "parameters": list(properties.keys()) if properties else []
            }

    # Add chat history context if available
    context_section = ""
    if chat_history:
        context_section = "\n\nPrevious conversation context:"
        for entry in chat_history[-5:]:  # Last 5 entries to avoid too much context
            if entry.get("type") == "user":
                context_section += f"\nUser: {entry.get('content', '')}"
            elif entry.get("type") == "assistant" and entry.get("executionData"):
                # Include execution results
                exec_data = entry["executionData"]
                if exec_data.get("state"):
                    for node_id, state in exec_data["state"].items():
                        if state.get("status") == "success" and state.get("output"):
                            output = state["output"]
                            if isinstance(output, dict) and "result" in output:
                                result = output["result"]
                                # Truncate long results for context
                                display_result = result[:200] + "..." if len(str(result)) > 200 else result
                                context_section += f"\nPrevious result from {node_id}: {display_result}"

    prompt = f"""Create a plan to: {user_goal}

Available tools: {', '.join(tool_names)}

Tool parameter schemas:
{json.dumps(tool_schemas, indent=2) if tool_schemas else "No schemas available"}{context_section}

IMPORTANT:
1. If the user is referring to data from previous messages (like "save it", "use that", etc.), create parameters that reference the specific previous results using {{{{node_id.output.field}}}} syntax.
2. For requests like "generate two cat facts" or "get multiple X", create PARALLEL nodes (no edges between them) that can run simultaneously.
3. For summarization using 'summarize' tool, use correct parameter names: 'text1', 'text2', 'style' (not 'facts' or other names). Use {{{{node1.output.result}}}} for text1, {{{{node2.output.result}}}} for text2, etc.
4. Use edges to show dependencies - independent tasks should have no edges between them.
5. Check tool schemas and use exact parameter names from the available tools.

Return ONLY this JSON format:
{{
  "plan": {{
    "plan_id": "plan-1",
    "nodes": [
      {{
        "id": "n1",
        "tool": "tool_name",
        "params_template": {{}},
        "metadata": {{"explain": "what this does"}}
      }}
    ],
    "edges": [],
    "explain": "brief explanation"
  }}
}}"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant that creates execution plans. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]

    # Use standard LLM interface - no logic branches
    content = call_llm(messages, max_tokens=500)

    try:
        # Try to parse as JSON
        parsed = json.loads(content)
        return parsed
    except json.JSONDecodeError:
        # Let LLM decide what to do if JSON parsing fails
        fix_prompt = f"""The previous response was not valid JSON: {content}

Please fix this and return ONLY valid JSON in the exact format requested for the goal: {user_goal}

Return ONLY this JSON format:
{{
  "plan": {{
    "plan_id": "plan-1",
    "nodes": [
      {{
        "id": "n1",
        "tool": "tool_name",
        "params_template": {{}},
        "metadata": {{"explain": "what this does"}}
      }}
    ],
    "edges": [],
    "explain": "brief explanation"
  }}
}}"""

        fix_messages = [
            {"role": "system", "content": "You are a helpful assistant that creates execution plans. Return only valid JSON."},
            {"role": "user", "content": fix_prompt}
        ]

        fixed_content = call_llm(fix_messages, max_tokens=500)
        try:
            return json.loads(fixed_content)
        except json.JSONDecodeError:
            # If LLM can't create valid JSON, let it handle this too
            raise RuntimeError(f"LLM failed to create valid JSON: {fixed_content}")
