"""LLM integration for memory_tool."""

from .client import LLMClient
from .prompts import TIMELINE_SUMMARY_PROMPT, CONVERSATION_SUMMARY_PROMPT, MODULE_SUMMARY_PROMPT

__all__ = [
    "LLMClient",
    "TIMELINE_SUMMARY_PROMPT",
    "CONVERSATION_SUMMARY_PROMPT",
    "MODULE_SUMMARY_PROMPT",
]
