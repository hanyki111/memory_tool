"""OpenAI Codex CLI client for headless LLM operations.

Uses ``codex exec``, so no API key is needed: the CLI's own login is used.
"""

from typing import List

from .cli_client import HeadlessCLIClient


class CodexCLIClient(HeadlessCLIClient):
    """Codex CLI in non-interactive mode."""

    DISPLAY_NAME = "Codex CLI"
    DEFAULT_COMMAND = "codex"
    CONFIG_SECTION = "codex_cli"
    INSTALL_HINT = "Install with: npm install -g @openai/codex"

    def _build_arguments(self) -> List[str]:
        arguments = [
            "exec",
            "--sandbox", "read-only",
            # The empty folder it runs in is not a repository.
            "--skip-git-repo-check",
            # A question about notes should not add to the user's session history.
            "--ephemeral",
        ]
        if self.model:
            arguments.extend(["--model", self.model])
        arguments.append("-")  # Read the prompt from stdin.
        return arguments
