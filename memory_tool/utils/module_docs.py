"""Find modules and their documents, whichever layout they use.

Three layouts are in use and all remain readable:
  1. ``<folder>/<folder>.md`` -- single document inside its own folder
  2. ``<folder>.md``          -- flat single document
  3. ``<folder>/current.md``  -- legacy multi-file module

Readers that opened ``current.md`` directly saw nothing in the first two
layouts, and reported a module with a large document as empty. Every reader
should go through this module instead.
"""

from pathlib import Path
from typing import List, Optional, Sequence

#: Files of the legacy multi-file layout, in reading order.
LEGACY_DOC_NAMES = (
    "module.md",
    "README.md",
    "interface.md",
    "dependencies.md",
    "current.md",
    "decisions.md",
)

#: Legacy files that mark their folder as a module during discovery.
#:
#: README.md is absent on purpose: a README in a plain folder is not a module.
LEGACY_MARKER_NAMES = (
    "module.md",
    "current.md",
    "decisions.md",
    "dependencies.md",
    "interface.md",
)

#: Legacy files preferred as a module's single main document.
LEGACY_MAIN_DOC_NAMES = ("current.md", "module.md")

#: Generated or retired files that are never modules, matched exactly.
#:
#: This is deliberately not "every uppercase stem": AI.md and MIGRATION-PLAN.md
#: are ordinary modules.
META_DOC_NAMES = frozenset({"PLAN.md", "MIGRATION-SUMMARY.md"})


def is_meta_document(filename: str) -> bool:
    """Tell whether a file is excluded from module discovery.

    Args:
        filename: File name including its suffix

    Returns:
        True for ``_``-prefixed files and the names in ``META_DOC_NAMES``.
        ``isupper`` covers a fully uppercase name such as ``NOTES.MD``.
    """
    return (
        filename.startswith("_")
        or filename.isupper()
        or filename in META_DOC_NAMES
    )


def _flat_document(module_path: Path) -> Path:
    # Appended rather than substituted: with_suffix would read a dot in the
    # module's own name as an extension and truncate it.
    return module_path.parent / f"{module_path.name}.md"


def resolve_module_document(module_path: Path) -> Optional[Path]:
    """Find a module's main document.

    Args:
        module_path: The module's folder, its path without a suffix, or the
            document itself

    Returns:
        Path to the main document, or None when the module has none.
    """
    if module_path.is_file():
        return module_path

    if module_path.is_dir():
        encapsulated = module_path / f"{module_path.name}.md"
        if encapsulated.is_file():
            return encapsulated

        for doc_name in LEGACY_MAIN_DOC_NAMES:
            legacy = module_path / doc_name
            if legacy.is_file():
                return legacy

    flat = _flat_document(module_path)
    if flat.is_file():
        return flat

    return None


def module_documents(
    module_path: Path,
    legacy_names: Sequence[str] = LEGACY_DOC_NAMES,
) -> List[Path]:
    """List the documents holding a module's content, main document first.

    Child modules and other files in the folder are not included: a folder may
    hold both a module's own document and its children.

    Args:
        module_path: The module's folder, or its path without a suffix
        legacy_names: Which legacy files to read, in order

    Returns:
        Existing documents. Empty when the module has none.
    """
    documents = []

    if module_path.is_dir():
        encapsulated = module_path / f"{module_path.name}.md"
        if encapsulated.is_file():
            documents.append(encapsulated)

        for doc_name in legacy_names:
            legacy = module_path / doc_name
            if legacy.is_file() and legacy not in documents:
                documents.append(legacy)

    flat = _flat_document(module_path)
    if flat.is_file():
        documents.append(flat)

    return documents


def read_module_text(
    module_path: Path,
    legacy_names: Sequence[str] = LEGACY_DOC_NAMES,
) -> str:
    """Read a module's content, joining its documents when there are several.

    Args:
        module_path: The module's folder, or its path without a suffix
        legacy_names: Which legacy files to read, in order

    Returns:
        The text, or an empty string when nothing readable exists. A legacy
        module's files are each preceded by a heading naming the file.
    """
    documents = module_documents(module_path, legacy_names)
    parts = []

    for document in documents:
        try:
            text = document.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        parts.append(f"## {document.name}\n\n{text}" if len(documents) > 1 else text)

    return "\n\n".join(parts)


def discover_module_paths(
    modules_path: Path,
    include_archived: bool = False,
) -> List[Path]:
    """Find every module under a modules folder.

    Args:
        modules_path: The ``modules`` directory
        include_archived: Also return modules under an archive folder

    Returns:
        Module paths relative to ``modules_path``, without a suffix, sorted.
    """
    if not modules_path.exists():
        return []

    modules = set()

    for md_file in modules_path.rglob("*.md"):
        relative = md_file.relative_to(modules_path)

        # Judged on the relative path so that a project stored under a folder
        # named "archive" does not lose all of its modules.
        if not include_archived and "archive" in relative.parts:
            continue
        if is_meta_document(md_file.name):
            continue

        if md_file.name in LEGACY_MARKER_NAMES or md_file.stem == md_file.parent.name:
            modules.add(relative.parent)
        else:
            modules.add(relative.parent / md_file.stem)

    return sorted(modules, key=str)
