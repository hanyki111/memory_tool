"""Ollama client for local LLM operations."""

from typing import Optional
import ollama


class OllamaClient:
    """Ollama client wrapper for local LLM."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Ollama client.

        Args:
            host: Ollama server host (optional, default: http://localhost:11434)
            model: Model name (optional, default: llama3.2)
        """
        from ..utils.config import Config

        config = Config()

        # Host priority: argument > config > default
        self.host = (
            host or config.get("llm.ollama_host") or "http://localhost:11434"
        )

        # Model priority: argument > config > default
        self.model = model or config.get("llm.ollama_model") or "llama3.2"

        # Create client
        self.client = ollama.Client(host=self.host)

    def summarize(
        self,
        content: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Summarize content using Ollama.

        Args:
            content: Content to summarize
            system_prompt: System prompt for summarization task
            max_tokens: Maximum tokens in response (optional, not used by Ollama)
            temperature: Temperature for generation (optional)

        Returns:
            Summary text

        Raises:
            Exception: If Ollama call fails
        """
        # Ollama doesn't use max_tokens, but we keep the interface consistent
        options = {}
        if temperature is not None:
            options["temperature"] = temperature

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                options=options if options else None,
            )

            # Extract text from response
            if response and "message" in response:
                return response["message"]["content"]
            else:
                raise ValueError("Empty response from Ollama")

        except Exception as e:
            raise Exception(f"Failed to summarize content with Ollama: {e}")

    def is_available(self) -> bool:
        """
        Check if Ollama is available (server running).

        Returns:
            True if Ollama server is accessible
        """
        try:
            # Try to list models to check if server is running
            self.client.list()
            return True
        except Exception:
            return False

    @classmethod
    def check_availability(cls, host: Optional[str] = None) -> bool:
        """
        Static method to check if Ollama is available without full initialization.

        Args:
            host: Ollama server host (optional)

        Returns:
            True if Ollama server is accessible
        """
        try:
            from ..utils.config import Config

            config = Config()
            host = host or config.get("llm.ollama_host") or "http://localhost:11434"

            client = ollama.Client(host=host)
            client.list()
            return True
        except Exception:
            return False
