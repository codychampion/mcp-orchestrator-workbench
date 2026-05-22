import json

def format_json(data: str, indent: int = 2) -> str:
    """Format and validate JSON data. Returns formatted JSON or an error message"""
    try:
        # Try to parse the JSON
        parsed = json.loads(data)

        # Format it nicely
        formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)

        return f"Valid JSON (formatted):\n{formatted}"
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {str(e)}"
    except Exception as e:
        return f"Error formatting JSON: {str(e)}"
