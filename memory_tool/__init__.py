"""Memory Tool - Time-Space Integrated Knowledge System."""

import re
from pathlib import Path


def _get_version() -> str:
    """Get version from pyproject.toml (editable install friendly)."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.exists():
        match = re.search(
            r'^version\s*=\s*"(.+?)"',
            pyproject.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            return match.group(1)
    # Fallback: installed package metadata
    try:
        from importlib.metadata import version
        return version("memory-tool")
    except Exception:
        return "0.0.0"


__version__ = _get_version()

__author__ = "Memory Tool Contributors"
