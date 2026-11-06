"""Writing guides: the questions and checks an AI uses to help with a document.

Guides are read by people and by AIs. They are never copied into a document and
no code parses their contents, so they can be edited freely. A file in
``<base>/guides/`` takes precedence over the bundled one of the same name.
"""

from pathlib import Path
from typing import Dict, Optional

#: Document types, in the order they are presented, mapped to their guide files.
DOCUMENT_TYPES: Dict[str, str] = {
    "참고": "reference",
    "이해": "understanding",
    "방법": "method",
    "판단": "judgment",
}

COMMON_GUIDE = "common"


class GuideError(Exception):
    """Raised when a guide cannot be found."""


def _bundled_guides() -> Path:
    return Path(__file__).parent.parent / "templates" / "guides"


def guide_file_name(guide: Optional[str]) -> str:
    """Resolve what the user asked for to a guide's file stem.

    Args:
        guide: A type in Korean (판단), a file stem (judgment), or None for the
            common guide

    Returns:
        The file stem.

    Raises:
        GuideError: If there is no such guide.
    """
    if not guide:
        return COMMON_GUIDE

    wanted = guide.strip().lower()

    if wanted in DOCUMENT_TYPES:
        return DOCUMENT_TYPES[wanted]
    if wanted == COMMON_GUIDE or wanted in DOCUMENT_TYPES.values():
        return wanted

    raise GuideError(f"No guide for '{guide}'. Types: {', '.join(DOCUMENT_TYPES)}")


def read_guide(guide: Optional[str] = None, base_path: Optional[Path] = None) -> str:
    """Read a writing guide.

    Args:
        guide: See ``guide_file_name``
        base_path: The knowledge base folder, for the user's own guides

    Returns:
        The guide's text.

    Raises:
        GuideError: If there is no such guide.
    """
    return read_guide_file(guide_file_name(guide), base_path)


def read_guide_file(stem: str, base_path: Optional[Path] = None) -> str:
    """Read a guide file by name, preferring the user's own copy.

    Args:
        stem: File name without its suffix
        base_path: The knowledge base folder, for the user's own guides

    Returns:
        The file's text.

    Raises:
        GuideError: If there is no such file.
    """
    candidates = []

    if base_path is not None:
        candidates.append(Path(base_path) / "guides" / f"{stem}.md")
    candidates.append(_bundled_guides() / f"{stem}.md")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    raise GuideError(f"Guide file is missing: {stem}.md")


def read_all_guides(base_path: Optional[Path] = None) -> str:
    """Read the common guide and every type's guide, joined."""
    stems = [COMMON_GUIDE, *DOCUMENT_TYPES.values()]
    return "\n\n".join(read_guide(stem, base_path) for stem in stems)
