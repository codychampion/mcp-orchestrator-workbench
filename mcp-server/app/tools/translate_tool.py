def translate(text: str, target_language: str = "spanish") -> str:
    """Translate text to target language. Supports: spanish, french, german, italian, portuguese, japanese, chinese"""
    # Mock translation - in a real implementation, you would use an LLM or translation API
    translations = {
        "spanish": {
            "hello": "hola",
            "goodbye": "adiós",
            "thank you": "gracias",
            "cat": "gato",
            "dog": "perro",
            "world": "mundo"
        },
        "french": {
            "hello": "bonjour",
            "goodbye": "au revoir",
            "thank you": "merci",
            "cat": "chat",
            "dog": "chien",
            "world": "monde"
        },
        "german": {
            "hello": "hallo",
            "goodbye": "auf wiedersehen",
            "thank you": "danke",
            "cat": "katze",
            "dog": "hund",
            "world": "welt"
        }
    }

    target_language = target_language.lower()

    if target_language not in ["spanish", "french", "german", "italian", "portuguese", "japanese", "chinese"]:
        return f"Error: Unsupported language '{target_language}'. Supported: spanish, french, german, italian, portuguese, japanese, chinese"

    # Simple word-by-word translation for demo
    text_lower = text.lower()
    if target_language in translations:
        for eng, trans in translations[target_language].items():
            text_lower = text_lower.replace(eng, trans)

    return f"[Translated to {target_language}] {text_lower}"
