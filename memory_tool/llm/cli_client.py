"""Shared base for LLM providers that run a coding agent's CLI headlessly.

These CLIs are agents that can edit files, but memory_tool only wants a text
answer. Each run therefore happens in an empty temporary folder, so that it can
neither touch the project nor pick up the project's own instructions, and each
provider adds whatever read-only mode its CLI has.

The prompt always travels on stdin. As a command-line argument, a long period
exceeds the Windows limit (about 8 KB through a .cmd shim, 32 KB otherwise).
"""

import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

TIMEOUT_SECONDS = 300


class HeadlessCLIClient:
    """Run a CLI once per request and return its answer as text."""

    #: Name used in messages.
    DISPLAY_NAME = "CLI"
    #: Command used when the configuration names none.
    DEFAULT_COMMAND = ""
    #: Section under ``llm`` in the configuration.
    CONFIG_SECTION = ""
    #: How to get the CLI, for the error shown when it is missing.
    INSTALL_HINT = ""

    def __init__(self, command: Optional[str] = None, model: Optional[str] = None):
        """Initialize the client.

        Args:
            command: CLI command. Defaults to the configured one.
            model: Model to use. Defaults to the configured one, then the CLI's.

        Raises:
            RuntimeError: If the CLI is not installed.
        """
        from ..utils.config import Config

        config = Config()
        self.command = command or self._configured_command(config)
        self.model = model or config.get(f"llm.{self.CONFIG_SECTION}.model")

        if not self._find_cli():
            raise RuntimeError(
                f"{self.DISPLAY_NAME} not found: {self.command}. {self.INSTALL_HINT}"
            )

    @classmethod
    def _configured_command(cls, config) -> str:
        return config.get(f"llm.{cls.CONFIG_SECTION}.command") or cls.DEFAULT_COMMAND

    def _find_cli(self) -> bool:
        return shutil.which(self.command) is not None

    def _build_arguments(self) -> List[str]:
        """Return the arguments after the executable."""
        raise NotImplementedError

    def _build_input(self, full_prompt: str) -> str:
        """Return what is written to the CLI's stdin."""
        return full_prompt

    def _parse_output(self, stdout: str) -> str:
        """Return the answer from the CLI's stdout."""
        return stdout

    def _extra_environment(self) -> Optional[Dict[str, str]]:
        """Return the process environment, or None to inherit it unchanged."""
        return None

    def _scrub(self, text: str) -> str:
        """Remove anything secret from text that may reach a message."""
        return text

    @staticmethod
    def _combine_prompt(user_content: str, system_prompt: Optional[str]) -> str:
        if system_prompt:
            return f"<system>\n{system_prompt}\n</system>\n\n{user_content}"
        return user_content

    def _call_cli(
        self,
        user_content: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Run the CLI once.

        Args:
            user_content: User message content
            system_prompt: System prompt, prepended to the content
            max_tokens: Not supported by these CLIs
            temperature: Not supported by these CLIs

        Returns:
            The answer.

        Raises:
            RuntimeError: If the CLI fails, times out or gives no answer.
        """
        # Resolved here because CreateProcess cannot start a .cmd by bare name.
        executable = shutil.which(self.command) or self.command
        command = [executable, *self._build_arguments()]
        stdin = self._build_input(self._combine_prompt(user_content, system_prompt))

        try:
            with tempfile.TemporaryDirectory(prefix="memory-tool-llm-") as empty_folder:
                result = subprocess.run(
                    command,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=TIMEOUT_SECONDS,
                    cwd=empty_folder,
                    env=self._extra_environment(),
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{self.DISPLAY_NAME} timed out after {TIMEOUT_SECONDS // 60} minutes")
        except OSError as e:
            raise RuntimeError(f"{self.DISPLAY_NAME} could not start: {e}")

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Unknown error").strip()
            raise RuntimeError(f"{self.DISPLAY_NAME} failed: {self._scrub(detail)[-1000:]}")

        answer = self._parse_output(result.stdout or "").strip()
        if not answer:
            raise RuntimeError(f"Empty response from {self.DISPLAY_NAME}")

        return answer

    def summarize(
        self,
        content: str,
        system_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Summarize content.

        Args:
            content: Content to summarize
            system_prompt: System prompt for the task
            max_tokens: Not supported by these CLIs
            temperature: Not supported by these CLIs

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
        """Generate text.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Not supported by these CLIs
            temperature: Not supported by these CLIs

        Returns:
            Generated text
        """
        return self._call_cli(prompt, system_prompt, max_tokens, temperature)

    def is_available(self) -> bool:
        """Tell whether the CLI is installed."""
        return self._find_cli()

    @classmethod
    def check_availability(cls, command: Optional[str] = None) -> bool:
        """Tell whether the CLI is installed, without creating a client.

        Args:
            command: CLI command. Defaults to the configured one.

        Returns:
            True if the command is found. Being installed does not prove it is
            logged in.
        """
        try:
            from ..utils.config import Config

            return shutil.which(command or cls._configured_command(Config())) is not None
        except Exception:
            return False


def environment_with(values: Dict[str, str]) -> Dict[str, str]:
    """Return this process's environment with ``values`` applied on top."""
    return {**os.environ, **values}
