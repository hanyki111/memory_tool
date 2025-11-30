"""Anthropic API client for LLM operations."""

import os
from typing import Optional
from anthropic import Anthropic, APIError
from ..utils.config import Config


class AnthropicClient:
    """Anthropic API client wrapper."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (optional, reads from config or env)
            model: Model name (optional, reads from config)
        """
        config = Config()

        # API key priority: argument > config > environment
        self.api_key = (
            api_key
            or config.get("llm.anthropic_api_key")
            or config.get("llm.api_key")  # backwards compatibility
            or os.getenv("ANTHROPIC_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or add 'llm.anthropic_api_key' to config.yaml"
            )

        # Model priority: argument > config > default
        self.model = (
            model
            or config.get("llm.anthropic_model")
            or config.get("llm.model")  # backwards compatibility
            or "claude-3-5-sonnet-20241022"
        )

        self.client = Anthropic(api_key=self.api_key)

        # Get settings from config
        self.max_tokens = config.get("llm.max_tokens") or 4096
        self.temperature = config.get("llm.temperature") or 0.7

    def _call_api(
        self,
        user_content: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Internal method to call Claude API.

        Args:
            user_content: User message content
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens in response (optional)
            temperature: Temperature for generation (optional)

        Returns:
            Response text

        Raises:
            APIError: If API call fails
            ValueError: If response is empty
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": user_content}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)

            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise ValueError("Empty response from API")

        except APIError as e:
            raise APIError(f"API call failed: {e}")

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
        """
        return self._call_api(content, system_prompt, max_tokens, temperature)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate text using Claude API.

        Args:
            prompt: User prompt for generation
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens in response (optional)
            temperature: Temperature for generation (optional)

        Returns:
            Generated text
        """
        return self._call_api(prompt, system_prompt, max_tokens, temperature)

    def is_available(self) -> bool:
        """
        Check if Anthropic is available (API key configured).

        Returns:
            True if API key is set
        """
        return bool(self.api_key)

    @classmethod
    def check_availability(cls) -> bool:
        """
        Static method to check if Anthropic is available without instantiation.

        Returns:
            True if API key is found in config or environment
        """
        try:
            config = Config().load()
            api_key = (
                config.get("llm.anthropic_api_key")
                or config.get("llm.api_key")
                or os.getenv("ANTHROPIC_API_KEY")
            )
            return bool(api_key)
        except Exception:
            return False
