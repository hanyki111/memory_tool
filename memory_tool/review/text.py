"""Messages shown by the review, in the configured language."""


def say(english: str, korean: str) -> str:
    """Pick a message by the ``help.language`` setting."""
    try:
        from memory_tool.utils.config import Config

        language = Config().get("help.language", "en")
    except Exception:
        language = "en"

    return korean if language == "ko" else english
