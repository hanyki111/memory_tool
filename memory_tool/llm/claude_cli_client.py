"""Claude CLI client for headless LLM operations.

Uses Claude Code CLI in print mode (-p) for non-interactive LLM calls.
This allows using Claude without API key, leveraging CLI authentication.
"""

import subprocess
import shutil
from typing import Optional


class ClaudeCLIClient:
    """Claude CLI wrapper for headless LLM operations."""

    def __init__(
        self,
        command: Optional[str] = None,
        model: Optional[str] = None,
        output_format: Optional[str] = None,
    ):
        """
        Initialize Claude CLI client.

        Args:
            command: CLI command (optional, default: claude)
            model: Model to use (optional, uses CLI default)
            output_format: Output format - 'text' or 'json' (optional, default: text)
        """
        from ..utils.config import Config

        config = Config()

        # Command priority: argument > config > default
        self.command = (
            command or config.get("llm.claude_cli.command") or "claude"
        )

        # Model priority: argument > config > None (use CLI default)
        self.model = model or config.get("llm.claude_cli.model")

        # Output format
        self.output_format = (
            output_format or config.get("llm.claude_cli.output_format") or "text"
        )

        # Verify CLI is available
        if not self._find_cli():
            raise RuntimeError(
                f"Claude CLI not found: {self.command}. "
                "Install with: npm install -g @anthropic-ai/claude-code"
            )

    def _find_cli(self) -> bool:
        """Check if Claude CLI is available in PATH."""
        return shutil.which(self.command) is not None

    def _call_cli(
        self,
        user_content: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Internal method to call Claude CLI.

        Args:
            user_content: User message content
            system_prompt: System prompt (optional, prepended to content)
            max_tokens: Maximum tokens in response (optional, uses --max-turns)
            temperature: Temperature for generation (not directly supported)

        Returns:
            Response text

        Raises:
            Exception: If CLI call fails
        """
        # Build command
        cmd = [self.command, "-p"]  # -p for print mode (non-interactive)

        # Add model if specified
        if self.model:
            cmd.extend(["--model", self.model])

        # Add output format
        if self.output_format == "json":
            cmd.extend(["--output-format", "json"])

        # Combine system prompt and user content
        if system_prompt:
            full_prompt = f"<system>\n{system_prompt}\n</system>\n\n{user_content}"
        else:
            full_prompt = user_content

        # Add prompt as argument
        cmd.append(full_prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                encoding="utf-8",
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                raise RuntimeError(f"Claude CLI failed: {error_msg}")

            response = result.stdout.strip()

            if not response:
                raise ValueError("Empty response from Claude CLI")

            # Parse JSON if needed
            if self.output_format == "json":
                import json
                try:
                    data = json.loads(response)
                    # Extract text from JSON response
                    if isinstance(data, dict):
                        return data.get("result", data.get("response", response))
                    return response
                except json.JSONDecodeError:
                    return response

            return response

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI timed out after 5 minutes")
        except Exception as e:
            raise RuntimeError(f"Claude CLI call failed: {e}")

    def summarize(
        self,
        content: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Summarize content using Claude CLI.

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
        Generate text using Claude CLI.

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
        Check if Claude CLI is available.

        Returns:
            True if Claude CLI is accessible
        """
        return self._find_cli()

    @classmethod
    def check_availability(cls, command: Optional[str] = None) -> bool:
        """
        Static method to check if Claude CLI is available without full initialization.

        Args:
            command: CLI command (optional)

        Returns:
            True if Claude CLI is accessible
        """
        try:
            from ..utils.config import Config

            config = Config()
            cmd = command or config.get("llm.claude_cli.command") or "claude"

            return shutil.which(cmd) is not None
        except Exception:
            return False
