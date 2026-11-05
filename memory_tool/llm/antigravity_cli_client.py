"""Google Antigravity CLI client for headless LLM operations.

Uses print mode of ``agy``, so no API key is needed: the CLI's own login is used.

Plain print mode takes the prompt only as an argument, which fails on long
periods (WinError 206 at about 40 KB), so the prompt goes through stream-json,
the one form that reads stdin. That form requires stream-json output as well.
"""

import json
from typing import List

from .cli_client import HeadlessCLIClient


#: Left to itself the agent starts by exploring the folder it runs in. Headless
#: mode denies those commands, as intended, and the turn ends with no answer.
_ANSWER_DIRECTLY = (
    "Everything you need is in this message. Do not use any tools, run commands or "
    "look at files. Reply directly with the requested text."
)


class AntigravityCLIClient(HeadlessCLIClient):
    """Antigravity CLI in print mode."""

    DISPLAY_NAME = "Antigravity CLI"
    DEFAULT_COMMAND = "agy"
    CONFIG_SECTION = "antigravity_cli"
    INSTALL_HINT = "See https://antigravity.google for installation."

    def _build_arguments(self) -> List[str]:
        arguments = [
            "--input-format=stream-json",
            "--output-format=stream-json",
            # Plan mode makes no changes.
            "--mode", "plan",
        ]
        if self.model:
            arguments.extend(["--model", self.model])
        # Attached with "=": a bare -p would take the next argument as its prompt.
        arguments.append("--print=")
        return arguments

    def _build_input(self, full_prompt: str) -> str:
        content = f"{_ANSWER_DIRECTLY}\n\n{full_prompt}"
        message = {"event": "user", "message": {"role": "user", "content": content}}
        return json.dumps(message, ensure_ascii=False) + "\n"

    def _parse_output(self, stdout: str) -> str:
        """Return the response from the final result event.

        Raises:
            RuntimeError: If the CLI reports a failure, or no result at all.
        """
        result = None

        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("event") == "result":
                result = event.get("result") or {}

        if result is None:
            raise RuntimeError(f"{self.DISPLAY_NAME} returned no result")

        if result.get("status") != "SUCCESS":
            detail = result.get("error") or result.get("status") or "Unknown error"
            raise RuntimeError(f"{self.DISPLAY_NAME} failed: {detail}")

        response = result.get("response", "")

        if not response.strip() and result.get("denied_actions"):
            denied = ", ".join(
                str(action.get("display_name") or action.get("action"))
                for action in result["denied_actions"]
            )
            raise RuntimeError(
                f"{self.DISPLAY_NAME} tried to use a tool instead of answering "
                f"and was denied: {denied}"
            )

        return response
