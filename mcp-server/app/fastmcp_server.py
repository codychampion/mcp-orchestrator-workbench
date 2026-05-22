#!/usr/bin/env python3
"""
FastMCP-based MCP server that exposes tools, resources, and prompts for DAG orchestration.
This replaces the FastAPI wrapper approach with native MCP implementation.
Includes a separate FastAPI app for config management HTTP endpoints.
"""

import json
import os
import time
from typing import List, Dict, Any
from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import threading
from tools.catfact_tool import get_cat_fact
from tools.echo_tool import echo
from tools.save_fact_tool import save_fact
from tools.calculate_tool import calculate
from tools.random_number_tool import random_number
from tools.translate_tool import translate
from tools.weather_tool import weather
from tools.search_tool import search
from tools.format_json_tool import format_json
from config_manager import get_config_manager

# Create FastMCP server instance
mcp = FastMCP("DAG Orchestration Server")

# Create separate FastAPI app for config management
config_app = FastAPI(title="MCP Config Manager")

# Add CORS middleware
config_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config manager
config_manager = get_config_manager()

# DAG-related tools
@mcp.tool()
def cat_fact() -> str:
    """Return a random cat fact from the internet"""
    return get_cat_fact()

@mcp.tool()
def echo(text: str) -> str:
    """Echo the provided text back to the user"""
    return text

@mcp.tool()
def save_fact(fact_text: str, category: str = "general") -> str:
    """Save a fact to the knowledge base with an optional category"""
    # Simple fact saving without hardcoded logic - let LLM handle the implementation
    return f"Saved fact in category '{category}': {fact_text[:100]}{'...' if len(fact_text) > 100 else ''}"

@mcp.tool()
def summarize(text1: str, text2: str = "", style: str = "concise") -> str:
    """Use LLM to summarize one or more pieces of text"""
    # Simple summarization without hardcoded logic
    combined_text = f"{text1}\n\n{text2}" if text2 else text1
    max_length = 200 if style == "concise" else 500

    if len(combined_text) <= max_length:
        return combined_text
    else:
        return combined_text[:max_length] + "... [truncated for brevity]"

# Register new tools with proper wrappers
@mcp.tool()
def calculate_tool(expression: str) -> str:
    """Evaluate a mathematical expression safely. Supports +, -, *, /, **, (), sqrt, abs, sin, cos, tan, log, exp"""
    return calculate(expression)

@mcp.tool()
def random_number_tool(min_val: int = 1, max_val: int = 100) -> str:
    """Generate a random integer between min_val and max_val (inclusive)"""
    return random_number(min_val, max_val)

@mcp.tool()
def translate_tool(text: str, target_language: str = "spanish") -> str:
    """Translate text to target language. Supports: spanish, french, german, italian, portuguese, japanese, chinese"""
    return translate(text, target_language)

@mcp.tool()
def weather_tool(location: str, units: str = "celsius") -> str:
    """Get current weather information for a location. Units can be 'celsius' or 'fahrenheit'"""
    return weather(location, units)

@mcp.tool()
def search_tool(query: str, num_results: int = 3) -> str:
    """Search for information on a topic (returns mock search results)"""
    return search(query, num_results)

@mcp.tool()
def format_json_tool(data: str, indent: int = 2) -> str:
    """Format and validate JSON data. Returns formatted JSON or an error message"""
    return format_json(data, indent)


# Config Management Endpoints (FastAPI routes on separate app)
class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]

class ParameterMappingRequest(BaseModel):
    wrong_name: str
    correct_name: str

class MetricsUpdateRequest(BaseModel):
    success: bool
    corrected: bool = False

class ExampleRequest(BaseModel):
    example: Dict[str, Any]


@config_app.get("/configs")
def get_all_configs():
    """Get all tool configurations"""
    configs = config_manager.load_all_configs()
    return {"status": "success", "configs": configs}


@config_app.get("/configs/{tool_name}")
def get_tool_config(tool_name: str):
    """Get configuration for a specific tool"""
    config = config_manager.load_tool_config(tool_name)
    if config:
        return {"status": "success", "tool_name": tool_name, "config": config}
    else:
        raise HTTPException(status_code=404, detail=f"Config not found for tool: {tool_name}")


@config_app.put("/configs/{tool_name}")
def update_tool_config(tool_name: str, request: ConfigUpdateRequest):
    """Update configuration for a specific tool"""
    success = config_manager.save_tool_config(tool_name, request.config)
    if success:
        return {"status": "success", "message": f"Config updated for {tool_name}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update config")


@config_app.post("/configs/{tool_name}/mappings")
def add_mapping(tool_name: str, request: ParameterMappingRequest):
    """Add a parameter name mapping to tool config"""
    success = config_manager.add_parameter_mapping(
        tool_name,
        request.wrong_name,
        request.correct_name
    )
    if success:
        return {
            "status": "success",
            "message": f"Added mapping: {request.wrong_name} → {request.correct_name}"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to add mapping")


@config_app.post("/configs/{tool_name}/metrics")
def update_metrics(tool_name: str, request: MetricsUpdateRequest):
    """Update optimization metrics for a tool"""
    success = config_manager.update_tool_metrics(
        tool_name,
        request.success,
        request.corrected
    )
    if success:
        return {"status": "success", "message": "Metrics updated"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update metrics")


@config_app.post("/configs/{tool_name}/examples")
def add_example(tool_name: str, request: ExampleRequest):
    """Add a training example to tool config"""
    success = config_manager.add_example(tool_name, request.example)
    if success:
        return {"status": "success", "message": "Example added"}
    else:
        raise HTTPException(status_code=500, detail="Failed to add example")


@config_app.get("/configs/summary/optimizations")
def get_optimization_summary():
    """Get summary of all optimizations across all tools"""
    summary = config_manager.get_optimization_summary()
    return {"status": "success", "summary": summary}


def run_config_api():
    """Run FastAPI config management server on port 8001"""
    uvicorn.run(config_app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"[MCP-SERVER] Starting FastMCP server on {host}:{port}")
    print(f"[MCP-SERVER] Starting Config API server on {host}:8001")
    print(f"[MCP-SERVER] Registered tools:")
    print(f"  - cat_fact: Get random cat facts")
    print(f"  - echo: Echo text back")
    print(f"  - save_fact: Save facts to knowledge base")
    print(f"  - summarize: Summarize text")
    print(f"  - calculate_tool: Evaluate math expressions")
    print(f"  - random_number_tool: Generate random numbers")
    print(f"  - translate_tool: Translate text to different languages")
    print(f"  - weather_tool: Get weather information")
    print(f"  - search_tool: Search for information")
    print(f"  - format_json_tool: Format and validate JSON")

    # Start Config API server in background thread
    config_thread = threading.Thread(target=run_config_api, daemon=True)
    config_thread.start()

    # Run FastMCP server with SSE transport (blocks)
    mcp.run(transport="sse", host=host, port=port)
