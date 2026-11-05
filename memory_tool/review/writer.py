"""Hand an item to an AI CLI for a writing conversation, or to the user's editor.

The CLIs' skill folders differ and may change, so nothing is installed into them.
Everything the AI needs goes into one work file, and it is told only to read that
file. Keeping the instruction short also avoids the Windows limit on command
lines, which is about 8 KB when the CLI is a .cmd shim.
"""

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from memory_tool.review.collector import collect_entries
from memory_tool.review.store import KIND_UPDATE, Item, Review, ReviewError
from memory_tool.review.text import say
from memory_tool.utils.module_docs import resolve_module_document

SOLO = "solo"

WRITE_PROCEDURE = Path(__file__).parent.parent / "templates" / "skills" / "mt-write" / "SKILL.md"


@dataclass(frozen=True)
class WritingTool:
    """An AI CLI that can hold a writing conversation."""

    key: str
    name: str
    #: The LLM provider that uses the same CLI.
    provider: str
    #: Section under ``llm`` in the configuration, which may name the command.
    config_section: str
    default_command: str
    #: Arguments before the instruction, which starts an interactive session.
    prompt_arguments: Tuple[str, ...] = ()


TOOLS = (
    WritingTool("claude", "Claude Code", "claude-cli", "claude_cli", "claude"),
    WritingTool("codex", "Codex", "codex-cli", "codex_cli", "codex"),
    WritingTool("antigravity", "Antigravity", "antigravity-cli", "antigravity_cli", "agy", ("-i",)),
)

_ALIASES = {
    "claude-cli": "claude",
    "codex-cli": "codex",
    "antigravity-cli": "antigravity",
    "agy": "antigravity",
}


def _config_value(key: str) -> Optional[str]:
    try:
        from memory_tool.utils.config import Config

        return Config().get(key)
    except Exception:
        return None


def tool_command(tool: WritingTool) -> str:
    """Return the command that starts a tool."""
    return _config_value(f"llm.{tool.config_section}.command") or tool.default_command


def installed_tools() -> List[WritingTool]:
    """List the tools found on this machine."""
    return [tool for tool in TOOLS if shutil.which(tool_command(tool))]


def resolve_choice(name: str) -> str:
    """Turn a name given with --with into a tool key, or ``SOLO``.

    Raises:
        ReviewError: If there is no such tool, or it is not installed.
    """
    wanted = name.strip().lower()
    wanted = _ALIASES.get(wanted, wanted)

    if wanted == SOLO:
        return SOLO

    for tool in TOOLS:
        if tool.key == wanted:
            if tool not in installed_tools():
                raise ReviewError(say(f"{tool.name} is not installed.", f"{tool.name}이(가) 설치되어 있지 않습니다."))
            return tool.key

    options = ", ".join([tool.key for tool in TOOLS] + [SOLO])
    raise ReviewError(say(f"Unknown tool: {name}. Choose from: {options}", f"알 수 없는 도구입니다: {name}. 선택지: {options}"))


def default_tool(installed: List[WritingTool]) -> Optional[WritingTool]:
    """Choose the tool offered by default.

    The ``review.writer`` setting wins. Without it, the CLI already used as the
    LLM provider is the natural choice, and otherwise the first one in the list.
    """
    configured = _config_value("review.writer")

    if configured:
        wanted = _ALIASES.get(configured, configured)
        for tool in installed:
            if tool.key == wanted:
                return tool

    provider = _config_value("llm.provider")
    wanted = _ALIASES.get(provider, provider)
    for tool in installed:
        if tool.key == wanted:
            return tool

    return installed[0] if installed else None


def _procedure_text(root: Path) -> str:
    """Read the writing procedure, preferring the project's own copy."""
    own = root / ".claude" / "skills" / "mt-write" / "SKILL.md"
    source = own if own.is_file() else WRITE_PROCEDURE
    return source.read_text(encoding="utf-8")


def evidence_lines(base: Path, days: List[str]) -> List[str]:
    """Read the entries of the given days, as lines to show or send."""
    lines = []

    for day in days:
        start = datetime.strptime(day, "%Y-%m-%d")
        end = start + timedelta(hours=23, minutes=59)
        for entry in collect_entries(base, start, end):
            lines.append(f"{entry.when:%Y-%m-%d %H:%M} | {entry.text}")

    return lines


def _task_text(base: Path, item: Item) -> str:
    lines = ["# The document to write", "", f"Topic: {item.title}"]

    if item.why:
        lines.append(f"Why it was proposed: {item.why}")
    if item.doc_type:
        lines.append(f"Suggested type: {item.doc_type}")

    if item.kind == KIND_UPDATE:
        document = resolve_module_document(Path(base) / "modules" / str(item.target))
        lines.append(f"Update this existing document: {document or item.target}")
        lines.append("Do not create a new document.")
    else:
        lines.append(f"This is a new document. Settle its path with the user, then run: mmodule create \"<path>\" --type {item.doc_type or '<type>'} --desc \"<one sentence>\"")

    if item.split_note:
        lines.append(
            f"The document has {item.split_note['lines']} lines and "
            f"{item.split_note['sections']} headings. Mention that it may be worth splitting, once."
        )

    lines.extend(["", "## Timeline entries this rests on", ""])
    lines.extend(f"- {line}" for line in evidence_lines(base, item.evidence))
    return "\n".join(lines)


def write_work_file(base: Path, name: str, content: str) -> Path:
    """Write a work file under the cache folder, which search does not read."""
    folder = Path(base) / ".cache" / "review"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _instruction(work_file: Path, root: Path) -> str:
    try:
        shown = os.path.relpath(work_file, root).replace("\\", "/")
    except ValueError:
        shown = str(work_file)

    return (
        f"Read the file {shown} and follow it. "
        "It tells you what we are doing. Speak to me in the language of the timeline entries."
    )


def run_tool(tool: WritingTool, work_file: Path, root: Path) -> None:
    """Run a CLI interactively in the project, and wait until the user leaves it.

    Permission prompts stay as the CLI has them. They are never skipped.

    Raises:
        ReviewError: If the CLI cannot start.
    """
    command = tool_command(tool)
    executable = shutil.which(command) or command
    arguments = [executable, *tool.prompt_arguments, _instruction(work_file, root)]

    try:
        subprocess.run(arguments, cwd=root)
    except OSError as e:
        raise ReviewError(say(f"Could not start {tool.name}: {e}", f"{tool.name}을(를) 실행할 수 없습니다: {e}"))


def write_with_tool(tool: WritingTool, base: Path, root: Path, review: Review, item: Item) -> None:
    """Hold a writing conversation about an item, then remove the work file."""
    content = "\n\n".join([
        "# Your instructions\n\nFollow the procedure below to help the user write the document described after it.",
        _procedure_text(root),
        _task_text(base, item),
    ])
    work_file = write_work_file(base, f"{review.name}-item-{item.number}", content)

    try:
        run_tool(tool, work_file, root)
    finally:
        work_file.unlink(missing_ok=True)


def open_in_editor(path: Path) -> None:
    """Open a file in the user's editor, or say where it is if that fails."""
    configured = os.environ.get("EDITOR") or ("notepad" if sys.platform == "win32" else "vi")
    command = shlex.split(configured, posix=sys.platform != "win32")

    try:
        subprocess.run([shutil.which(command[0]) or command[0], *command[1:], str(path)], check=True)
    except (OSError, subprocess.CalledProcessError):
        print(say(f"Could not open an editor. Edit this file: {path}", f"편집기를 열 수 없습니다. 이 파일을 직접 고쳐 주세요: {path}"))


def suggested_path(title: str) -> str:
    """Suggest a module path from a title."""
    return "-".join(title.split())
