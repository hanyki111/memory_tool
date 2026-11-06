"""One-line JSON results for editors, scripts and other programs.

Every ``--json`` command prints exactly one line on standard output:

- success: ``{"ok": true, ...}``
- failure: ``{"ok": false, "code": "...", "error": "..."}``

``code`` is what a caller decides on; ``error`` is for a person and stays mostly
in English. Messages meant for a person, such as the review notice, go in a
``notices`` list as ``{"kind", "message"}``.

Progress text is never printed in JSON mode, so a caller can read the last line
that parses as JSON, or the only line there is.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional

from memory_tool.core.timeline import parse_entry_lines

NOT_INITIALIZED = "not_initialized"
INVALID_ARGUMENT = "invalid_argument"
NOT_FOUND = "not_found"
FUTURE_TIME = "future_time"
DISTANT_PAST = "distant_past"
LLM_UNAVAILABLE = "llm_unavailable"
LLM_FAILED = "llm_failed"
FAILED = "failed"


def emit(payload: Dict[str, Any]) -> None:
    """Print one line of JSON, always as UTF-8.

    Uses the raw stream rather than rich, which hard-wraps at the terminal
    width, and rather than the locale encoding, which on Windows is not UTF-8
    when the output is piped to another program.
    """
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    sys.stdout.flush()

    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(line)
        sys.stdout.flush()
        return

    buffer.write(line.encode("utf-8"))
    buffer.flush()


def succeed(**fields: Any) -> None:
    """Print a success result."""
    emit({"ok": True, **fields})


def fail(code: str, message: str, **fields: Any) -> NoReturn:
    """Print a failure result and exit with status 1."""
    emit({"ok": False, "code": code, "error": message, **fields})
    sys.exit(1)


def notice(kind: str, message: str) -> Dict[str, str]:
    """Build one entry of a ``notices`` list."""
    return {"kind": kind, "message": message}


def date_text(value: Optional[Any]) -> Optional[str]:
    """Write a date as YYYY-MM-DD, or None."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


def path_text(path: Optional[Path]) -> Optional[str]:
    """Write a path as an absolute path, which a caller can open directly."""
    if path is None:
        return None
    return str(Path(path).resolve())


def entry_dict(day: Any, entry: Dict[str, Any]) -> Dict[str, Any]:
    """One entry, as views and search results carry it."""
    return {"date": date_text(day), "time": entry["time"], "text": entry["text"], "tags": entry["tags"]}


def day_dict(day: Any, path: Path, content: str) -> Dict[str, Any]:
    """One day of a timeline view.

    ``content`` keeps lines that are not entries, such as notes written by hand,
    which ``entries`` leaves out.
    """
    return {
        "date": date_text(day),
        "path": path_text(path),
        "entries": [entry_dict(day, entry) for entry in parse_entry_lines(content)],
        "content": content,
    }


def days_payload(start: Any, end: Any, days: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The fields of a timeline view result."""
    return {"from": date_text(start), "to": date_text(end), "days": days}
