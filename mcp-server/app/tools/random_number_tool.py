import random

def random_number(min_val: int = 1, max_val: int = 100) -> str:
    """Generate a random integer between min_val and max_val (inclusive)"""
    try:
        if min_val > max_val:
            return f"Error: min_val ({min_val}) must be less than or equal to max_val ({max_val})"

        number = random.randint(min_val, max_val)
        return f"Random number between {min_val} and {max_val}: {number}"
    except Exception as e:
        return f"Error generating random number: {str(e)}"
