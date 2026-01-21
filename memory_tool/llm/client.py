"""LLM client factory for multiple providers."""

from typing import Optional, Literal
from ..utils.config import Config


# Supported provider types
ProviderType = Literal["anthropic", "ollama", "claude-cli", "gemini-cli"]


class LLMClient:
    """
    LLM client factory that creates appropriate client based on provider.

    Supports:
    - anthropic: Claude API (cloud, requires API key)
    - ollama: Local LLM (free, requires Ollama running)
    - claude-cli: Claude Code CLI in headless mode (uses CLI auth)
    - gemini-cli: Gemini CLI in headless mode (uses CLI auth)
    """

    def __new__(
        cls,
        provider: Optional[ProviderType] = None,
        **kwargs,
    ):
        """
        Create appropriate LLM client based on provider.

        Args:
            provider: LLM provider. If None, reads from config.
                - 'anthropic': Claude API (requires API key)
                - 'ollama': Local LLM (requires Ollama server)
                - 'claude-cli': Claude Code CLI (requires CLI installed)
                - 'gemini-cli': Gemini CLI (requires CLI installed)
            **kwargs: Provider-specific arguments

        Returns:
            Appropriate LLM client instance

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

        elif provider == "claude-cli":
            from .claude_cli_client import ClaudeCLIClient

            return ClaudeCLIClient(**kwargs)

        elif provider == "gemini-cli":
            from .gemini_cli_client import GeminiCLIClient

            return GeminiCLIClient(**kwargs)

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Supported providers: anthropic, ollama, claude-cli, gemini-cli"
            )

    @classmethod
    def check_availability(cls, provider: Optional[str] = None) -> bool:
        """
        Check if LLM is available for given provider.

        Args:
            provider: LLM provider. If None, reads from config.
                - 'anthropic': Claude API
                - 'ollama': Local LLM
                - 'claude-cli': Claude Code CLI
                - 'gemini-cli': Gemini CLI

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

            elif provider == "claude-cli":
                from .claude_cli_client import ClaudeCLIClient

                return ClaudeCLIClient.check_availability()

            elif provider == "gemini-cli":
                from .gemini_cli_client import GeminiCLIClient

                return GeminiCLIClient.check_availability()

            else:
                return False

        except Exception:
            return False

    @classmethod
    def get_provider(cls) -> str:
        """
        Get current LLM provider from config.

        Returns:
            Provider name (anthropic, ollama, claude-cli, gemini-cli)
        """
        try:
            config = Config()
            return config.get("llm.provider") or "anthropic"
        except Exception:
            return "anthropic"

    @classmethod
    def list_available_providers(cls) -> list:
        """
        List all available LLM providers.

        Returns:
            List of available provider names
        """
        available = []

        # Check each provider
        providers = ["anthropic", "ollama", "claude-cli", "gemini-cli"]
        for provider in providers:
            if cls.check_availability(provider):
                available.append(provider)

        return available
