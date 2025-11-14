"""LLM client factory for multiple providers."""

from typing import Optional, Literal
from ..utils.config import Config


class LLMClient:
    """
    LLM client factory that creates appropriate client based on provider.

    Supports:
    - anthropic: Claude API (cloud, requires API key)
    - ollama: Local LLM (free, requires Ollama running)
    """

    def __new__(
        cls,
        provider: Optional[Literal["anthropic", "ollama"]] = None,
        **kwargs,
    ):
        """
        Create appropriate LLM client based on provider.

        Args:
            provider: LLM provider ('anthropic' or 'ollama'). If None, reads from config.
            **kwargs: Provider-specific arguments

        Returns:
            AnthropicClient or OllamaClient instance

        Raises:
            ValueError: If provider is invalid or not configured
        """
        config = Config()

        # Determine provider
        if provider is None:
            provider = config.get("llm.provider") or "anthropic"

        provider = provider.lower()

        # Create appropriate client
        if provider == "anthropic":
            from .anthropic_client import AnthropicClient

            return AnthropicClient(**kwargs)

        elif provider == "ollama":
            from .ollama_client import OllamaClient

            return OllamaClient(**kwargs)

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Supported providers: anthropic, ollama"
            )

    @classmethod
    def check_availability(cls, provider: Optional[str] = None) -> bool:
        """
        Check if LLM is available for given provider.

        Args:
            provider: LLM provider ('anthropic' or 'ollama'). If None, reads from config.

        Returns:
            True if provider is configured and available
        """
        try:
            config = Config()

            # Determine provider
            if provider is None:
                provider = config.get("llm.provider") or "anthropic"

            provider = provider.lower()

            # Check availability
            if provider == "anthropic":
                from .anthropic_client import AnthropicClient

                return AnthropicClient.check_availability()

            elif provider == "ollama":
                from .ollama_client import OllamaClient

                return OllamaClient.check_availability()

            else:
                return False

        except Exception:
            return False

    @classmethod
    def get_provider(cls) -> str:
        """
        Get current LLM provider from config.

        Returns:
            Provider name ('anthropic' or 'ollama')
        """
        try:
            config = Config()
            return config.get("llm.provider") or "anthropic"
        except Exception:
            return "anthropic"
