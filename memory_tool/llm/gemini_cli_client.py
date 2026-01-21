"""Gemini CLI client for headless LLM operations.

Uses Google's Gemini CLI for non-interactive LLM calls.
This allows using Gemini without API key, leveraging CLI authentication.
"""

import subprocess
import shutil
from typing import Optional


class GeminiCLIClient:
    """Gemini CLI wrapper for headless LLM operations."""

    def __init__(
        self,
        command: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize Gemini CLI client.

        Args:
            command: CLI command (optional, default: gemini)
            model: Model to use (optional, uses CLI default)
        """
        from ..utils.config import Config

        config = Config()

        # Command priority: argument > config > default
        self.command = (
            command or config.get("llm.gemini_cli.command") or "gemini"
        )

        # Model priority: argument > config > None (use CLI default)
        self.model = model or config.get("llm.gemini_cli.model")

        # Verify CLI is available
        if not self._find_cli():
            raise RuntimeError(
                f"Gemini CLI not found: {self.command}. "
                "Install with: npm install -g @anthropic-ai/gemini-cli or check Google's official CLI"
            )

    def _find_cli(self) -> bool:
        """Check if Gemini CLI is available in PATH."""
        return shutil.which(self.command) is not None

    def _call_cli(
        self,
        user_content: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Internal method to call Gemini CLI.

        Args:
            user_content: User message content
            system_prompt: System prompt (optional, prepended to content)
            max_tokens: Maximum tokens in response (optional)
            temperature: Temperature for generation (optional)

        Returns:
            Response text

        Raises:
            Exception: If CLI call fails
        """
        # Build command
        cmd = [self.command]

        # Add model if specified
        if self.model:
            cmd.extend(["--model", self.model])

        # Combine system prompt and user content
        if system_prompt:
            full_prompt = f"System instructions: {system_prompt}\n\nUser request: {user_content}"
        else:
            full_prompt = user_content

        try:
            # Use stdin to pass prompt (more reliable for long prompts)
            result = subprocess.run(
                cmd,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                encoding="utf-8",
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                raise RuntimeError(f"Gemini CLI failed: {error_msg}")

            response = result.stdout.strip()

            if not response:
                raise ValueError("Empty response from Gemini CLI")

            return response

        except subprocess.TimeoutExpired:
            raise RuntimeError("Gemini CLI timed out after 5 minutes")
        except Exception as e:
            raise RuntimeError(f"Gemini CLI call failed: {e}")

    def summarize(
        self,
        content: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Summarize content using Gemini CLI.

        Args:
            content: Content to summarize
            system_prompt: System prompt for summarization task
            max_tokens: Maximum tokens in response (optional)
            temperature: Temperature for generation (optional)

        Returns:
            Summary text
        """
        return self._call_cli(content, system_prompt, max_tokens, temperature)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate text using Gemini CLI.

        Args:
            prompt: User prompt for generation
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens in response (optional)
            temperature: Temperature for generation (optional)

        Returns:
            Generated text
        """
        return self._call_cli(prompt, system_prompt, max_tokens, temperature)

    def is_available(self) -> bool:
        """
        Check if Gemini CLI is available.

        Returns:
            True if Gemini CLI is accessible
        """
        return self._find_cli()

    @classmethod
    def check_availability(cls, command: Optional[str] = None) -> bool:
        """
        Static method to check if Gemini CLI is available without full initialization.

        Args:
            command: CLI command (optional)

        Returns:
            True if Gemini CLI is accessible
        """
        try:
            from ..utils.config import Config

            config = Config()
            cmd = command or config.get("llm.gemini_cli.command") or "gemini"

            return shutil.which(cmd) is not None
        except Exception:
            return False
