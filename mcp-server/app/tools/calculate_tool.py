import re
import math

def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely. Supports +, -, *, /, **, (), sqrt, abs, sin, cos, tan, log, exp"""
    try:
        # Remove any potentially dangerous characters
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.\,]+$', expression.replace('sqrt', '').replace('abs', '').replace('sin', '').replace('cos', '').replace('tan', '').replace('log', '').replace('exp', '').replace('**', '')):
            return f"Error: Invalid characters in expression. Only numbers and operators allowed."

        # Safe evaluation using allowed math functions
        allowed_names = {
            'sqrt': math.sqrt,
            'abs': abs,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e
        }

        # Evaluate the expression
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"
