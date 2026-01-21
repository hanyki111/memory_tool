"""LLM integration for memory_tool."""

from .client import LLMClient
from .prompts import TIMELINE_SUMMARY_PROMPT, CONVERSATION_SUMMARY_PROMPT, MODULE_SUMMARY_PROMPT

# Optional imports for direct client access
try:
    from .anthropic_client import AnthropicClient
except ImportError:
    AnthropicClient = None

try:
    from .ollama_client import OllamaClient
except ImportError:
    OllamaClient = None

try:
    from .claude_cli_client import ClaudeCLIClient
except ImportError:
    ClaudeCLIClient = None

try:
    from .gemini_cli_client import GeminiCLIClient
except ImportError:
    GeminiCLIClient = None

__all__ = [
    "LLMClient",
    "AnthropicClient",
    "OllamaClient",
    "ClaudeCLIClient",
    "GeminiCLIClient",
    "TIMELINE_SUMMARY_PROMPT",
    "CONVERSATION_SUMMARY_PROMPT",
    "MODULE_SUMMARY_PROMPT",
]
