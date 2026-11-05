"""GLM through the Claude CLI.

GLM offers an endpoint the Claude CLI can talk to, so this provider is the same
CLI with its connection variables pointed elsewhere. There is no separate API
client to maintain, at the cost of needing the Claude CLI installed.

The configuration holds only where the values are, never the values, because the
knowledge base folder is often synced or committed::

    llm:
      provider: glm
      glm:
        env_from_ps1: E:/secrets/set-glm.ps1     # $env:NAME = 'value' lines
        env_from_env:                            # or: variable -> variable to read
          ANTHROPIC_AUTH_TOKEN: GLM_API_KEY
          ANTHROPIC_BASE_URL: GLM_BASE_URL
        model: opus
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional

from .claude_cli_client import ClaudeCLIClient
from .cli_client import environment_with

_PS1_ASSIGNMENT = re.compile(
    r"""^\s*\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:(['"])(.*)\2|([^\s'"#]+))\s*(?:#.*)?$"""
)

#: Only Claude CLI connection variables are taken from a settings file, which may
#: well hold unrelated values.
_ALLOWED_PREFIXES = ("ANTHROPIC_", "CLAUDE_CODE_", "API_TIMEOUT_MS")

#: The Claude CLI prefers an API key over a token. One inherited from the user's
#: environment would be sent to the GLM endpoint, so it must not pass through.
_INHERITED_CREDENTIALS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

_MIN_SECRET_LENGTH = 8


def read_ps1_environment(path: Path) -> Dict[str, str]:
    """Read connection variables from a PowerShell settings file.

    Args:
        path: File with ``$env:NAME = 'value'`` lines

    Returns:
        The Claude CLI connection variables it sets.
    """
    values = {}

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = _PS1_ASSIGNMENT.match(line)
        if match and match.group(1).startswith(_ALLOWED_PREFIXES):
            values[match.group(1)] = match.group(3) if match.group(2) else match.group(4)

    return values


def load_connection(settings: Optional[dict]) -> Dict[str, str]:
    """Collect the GLM connection variables.

    Args:
        settings: The ``llm.glm`` configuration section

    Returns:
        The variables.

    Raises:
        RuntimeError: If the base URL or a credential is missing. The message
            names the settings, never a value.
    """
    settings = settings or {}
    values: Dict[str, str] = {}

    source = settings.get("env_from_ps1")
    if source:
        path = Path(source).expanduser()
        if not path.is_file():
            raise RuntimeError(f"GLM settings file not found: {path}")
        values.update(read_ps1_environment(path))

    for name, variable in (settings.get("env_from_env") or {}).items():
        if variable in os.environ:
            values[name] = os.environ[variable]

    has_credential = values.get("ANTHROPIC_AUTH_TOKEN") or values.get("ANTHROPIC_API_KEY")
    if not values.get("ANTHROPIC_BASE_URL") or not has_credential:
        raise RuntimeError(
            "GLM needs ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN. "
            "Set llm.glm.env_from_ps1 or llm.glm.env_from_env in config.yaml."
        )

    return values


class GLMClient(ClaudeCLIClient):
    """The Claude CLI connected to GLM."""

    DISPLAY_NAME = "GLM (via Claude CLI)"
    CONFIG_SECTION = "glm"

    def __init__(
        self,
        command: Optional[str] = None,
        model: Optional[str] = None,
        output_format: Optional[str] = None,
    ):
        """Initialize the client.

        Args:
            command: Claude CLI command
            model: Model name as the Claude CLI knows it. Defaults to ``opus``,
                which the settings usually map to a GLM model.
            output_format: ``text`` or ``json``

        Raises:
            RuntimeError: If the connection is not configured or the CLI is missing.
        """
        from ..utils.config import Config

        self._connection = load_connection(Config().get("llm.glm"))
        super().__init__(command, model, output_format)
        self.model = self.model or "opus"

    @classmethod
    def _configured_command(cls, config) -> str:
        return (
            config.get("llm.glm.command")
            or config.get("llm.claude_cli.command")
            or cls.DEFAULT_COMMAND
        )

    def _extra_environment(self) -> Dict[str, str]:
        environment = environment_with(self._connection)
        for name in _INHERITED_CREDENTIALS:
            if name not in self._connection:
                environment.pop(name, None)
        return environment

    def _scrub(self, text: str) -> str:
        for value in self._connection.values():
            if len(value) >= _MIN_SECRET_LENGTH:
                text = text.replace(value, "(hidden)")
        return text

    @classmethod
    def check_availability(cls, command: Optional[str] = None) -> bool:
        """Tell whether the Claude CLI is installed and the connection is configured."""
        try:
            from ..utils.config import Config

            load_connection(Config().get("llm.glm"))
        except Exception:
            return False

        return super().check_availability(command)
