"""LLM client factory for multiple providers."""

from importlib import import_module
from typing import Dict, Literal, Optional, Tuple

from ..utils.config import Config

# Supported provider types
ProviderType = Literal[
    "anthropic", "claude-cli", "codex-cli", "antigravity-cli", "glm", "ollama"
]

#: Provider name -> (module under memory_tool.llm, client class).
_PROVIDERS: Dict[str, Tuple[str, str]] = {
    "anthropic": ("anthropic_client", "AnthropicClient"),
    "claude-cli": ("claude_cli_client", "ClaudeCLIClient"),
    "codex-cli": ("codex_cli_client", "CodexCLIClient"),
    "antigravity-cli": ("antigravity_cli_client", "AntigravityCLIClient"),
    "glm": ("glm_client", "GLMClient"),
    "ollama": ("ollama_client", "OllamaClient"),
}

_ALIASES = {
    "claude": "claude-cli",
    "codex": "codex-cli",
    "antigravity": "antigravity-cli",
    "agy": "antigravity-cli",
}

#: Removed providers -> why, for a setting that still names one.
_REMOVED = {
    "gemini-cli": (
        "The gemini-cli provider was removed: Gemini CLI no longer serves individual "
        "Code Assist accounts. Use antigravity-cli instead."
    ),
}


class LLMClient:
    """
    LLM client factory that creates appropriate client based on provider.

    Supports:
    - anthropic: Claude API (requires an API key)
    - claude-cli: Claude Code CLI in headless mode (uses CLI login)
    - codex-cli: OpenAI Codex CLI in headless mode (uses CLI login)
    - antigravity-cli: Google Antigravity CLI in headless mode (uses CLI login)
    - glm: GLM through the Claude CLI (needs llm.glm settings)
    - ollama: Local LLM (requires Ollama running)
    """

    #: Tried in this order when no provider is configured. This is only a
    #: fallback for an unset configuration. glm is absent because it reaches a
    #: separate paid service, which should be chosen deliberately.
    PROVIDER_ORDER = ("anthropic", "claude-cli", "codex-cli", "antigravity-cli", "ollama")

    def __new__(
        cls,
        provider: Optional[ProviderType] = None,
        **kwargs,
    ):
        """
        Create appropriate LLM client based on provider.

        Args:
            provider: LLM provider. If None, uses ``get_provider``.
            **kwargs: Provider-specific arguments

        Returns:
            Appropriate LLM client instance

        Raises:
            ValueError: If provider is invalid or removed
        """
        name = cls.normalize(provider or cls.get_provider())

        if name in _REMOVED:
            raise ValueError(_REMOVED[name])

        if name not in _PROVIDERS:
            raise ValueError(
                f"Unknown LLM provider: {name}. "
                f"Supported providers: {', '.join(_PROVIDERS)}"
            )

        return cls._client_class(name)(**kwargs)

    @staticmethod
    def normalize(provider: str) -> str:
        """Turn a provider name or alias into its canonical name."""
        name = provider.strip().lower()
        return _ALIASES.get(name, name)

    @staticmethod
    def _client_class(name: str):
        # Imported on demand so that one provider's optional dependency cannot
        # stop the others from working.
        module, class_name = _PROVIDERS[name]
        return getattr(import_module(f".{module}", __package__), class_name)

    @classmethod
    def check_availability(cls, provider: Optional[str] = None) -> bool:
        """
        Check if LLM is available for given provider.

        Args:
            provider: LLM provider. If None, uses ``get_provider``.

        Returns:
            True if provider is configured and available. For a CLI this means
            installed, which does not prove it is logged in.
        """
        try:
            name = cls.normalize(provider or cls.get_provider())

            if name not in _PROVIDERS:
                return False

            return cls._client_class(name).check_availability()

        except Exception:
            return False

    @classmethod
    def get_provider(cls) -> str:
        """
        Get the LLM provider to use.

        The configured provider wins, even when it is unavailable, so that a
        broken setting is reported rather than silently replaced. Without one,
        the first available provider is used.

        Returns:
            Provider name
        """
        try:
            configured = Config().get("llm.provider")
        except Exception:
            configured = None

        if configured:
            return cls.normalize(configured)

        for provider in cls.PROVIDER_ORDER:
            if cls.check_availability(provider):
                return provider

        return cls.PROVIDER_ORDER[0]

    @classmethod
    def removed_provider_notice(cls, provider: Optional[str] = None) -> Optional[str]:
        """Explain a provider that no longer exists.

        Args:
            provider: Provider name. If None, the configured one.

        Returns:
            The explanation, or None if the provider was not removed.
        """
        try:
            name = provider or Config().get("llm.provider")
        except Exception:
            return None

        return _REMOVED.get(cls.normalize(name)) if name else None

    @classmethod
    def list_available_providers(cls) -> list:
        """
        List all available LLM providers.

        Returns:
            Available provider names, those tried automatically first.
        """
        others = [name for name in _PROVIDERS if name not in cls.PROVIDER_ORDER]
        return [
            provider
            for provider in (*cls.PROVIDER_ORDER, *others)
            if cls.check_availability(provider)
        ]
