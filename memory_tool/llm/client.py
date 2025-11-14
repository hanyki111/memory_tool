"""Anthropic API client for LLM operations."""

import os
from typing import Optional
from anthropic import Anthropic, APIError
from ..utils.config import Config


class LLMClient:
    """Anthropic API client wrapper."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            api_key: Anthropic API key (optional, reads from config or env)
            model: Model name (optional, reads from config)
        """
        self.config = Config.load()

        # API key priority: argument > config > environment
        self.api_key = (
            api_key
            or self.config.get("llm.api_key")
            or os.getenv("ANTHROPIC_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or add 'llm.api_key' to config.yaml"
            )

        # Model priority: argument > config > default
        self.model = (
            model
            or self.config.get("llm.model")
            or "claude-3-5-sonnet-20241022"
        )

        self.client = Anthropic(api_key=self.api_key)

        # Get settings from config
        self.max_tokens = self.config.get("llm.max_tokens") or 4096
        self.temperature = self.config.get("llm.temperature") or 0.7

    def summarize(
        self,
        content: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Summarize content using Claude API.

        Args:
            content: Content to summarize
            system_prompt: System prompt for summarization task
            max_tokens: Maximum tokens in response (optional)
            temperature: Temperature for generation (optional)

        Returns:
            Summary text

        Raises:
            APIError: If API call fails
            ValueError: If content is too long
        """
        # Use provided values or fall back to instance defaults
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise ValueError("Empty response from API")

        except APIError as e:
            raise APIError(f"Failed to summarize content: {e}")

    def is_available(self) -> bool:
        """
        Check if LLM is available (API key configured).

        Returns:
            True if API key is set
        """
        return bool(self.api_key)

    @classmethod
    def check_availability(cls) -> bool:
        """
        Static method to check if LLM is available without instantiation.

        Returns:
            True if API key is found in config or environment
        """
        try:
            config = Config.load()
            api_key = config.get("llm.api_key") or os.getenv("ANTHROPIC_API_KEY")
            return bool(api_key)
        except Exception:
            return False
