"""Claude Code CLI client for headless LLM operations.

Uses print mode (-p), so no API key is needed: the CLI's own login is used.
"""

import json
from typing import List, Optional

from .cli_client import HeadlessCLIClient


class ClaudeCLIClient(HeadlessCLIClient):
    """Claude Code CLI in print mode."""

    DISPLAY_NAME = "Claude CLI"
    DEFAULT_COMMAND = "claude"
    CONFIG_SECTION = "claude_cli"
    INSTALL_HINT = "Install with: npm install -g @anthropic-ai/claude-code"

    def __init__(
        self,
        command: Optional[str] = None,
        model: Optional[str] = None,
        output_format: Optional[str] = None,
    ):
        """Initialize the client.

        Args:
            command: CLI command. Defaults to the configured one, then ``claude``.
            model: Model. Defaults to the configured one, then the CLI's.
            output_format: ``text`` or ``json``. Defaults to the configured one.
        """
        from ..utils.config import Config

        self.output_format = (
            output_format or Config().get("llm.claude_cli.output_format") or "text"
        )
        super().__init__(command, model)

    def _build_arguments(self) -> List[str]:
        arguments = ["-p"]
        if self.model:
            arguments.extend(["--model", self.model])
        if self.output_format == "json":
            arguments.extend(["--output-format", "json"])
        return arguments

    def _parse_output(self, stdout: str) -> str:
        if self.output_format != "json":
            return stdout

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout

        if isinstance(data, dict):
            return data.get("result", data.get("response", stdout))
        return stdout
