"""Conversation summarization functionality."""

from typing import Optional
from ..llm.client import LLMClient
from ..llm.prompts import CONVERSATION_SUMMARY_PROMPT


class ConversationSummarizer:
    """Summarize Claude Code conversations using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize conversation summarizer.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
        """
        self.llm_client = llm_client or LLMClient()

    def summarize(self, conversation: str) -> str:
        """
        Summarize a conversation.

        Args:
            conversation: Full conversation text

        Returns:
            Summary text

        Raises:
            ValueError: If conversation is empty
        """
        if not conversation.strip():
            raise ValueError("Conversation is empty")

        # Generate summary
        summary = self.llm_client.summarize(
            content=conversation,
            system_prompt=CONVERSATION_SUMMARY_PROMPT,
        )

        return summary

    def summarize_session(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Summarize a conversation session from message list.

        Args:
            messages: List of messages with 'role' and 'content' keys

        Returns:
            Summary text

        Raises:
            ValueError: If messages list is empty
        """
        if not messages:
            raise ValueError("Messages list is empty")

        # Format messages as conversation
        conversation_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                conversation_parts.append(f"User: {content}")
            elif role == "assistant":
                conversation_parts.append(f"Assistant: {content}")
            elif role == "system":
                conversation_parts.append(f"System: {content}")
            else:
                conversation_parts.append(f"{role}: {content}")

        conversation = "\n\n".join(conversation_parts)

        return self.summarize(conversation)
