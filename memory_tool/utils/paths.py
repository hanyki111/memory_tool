"""Central resolution of the memory base folder.

Single source of truth for *where* the knowledge base lives.

Historically the base folder was hardcoded as ``.memory`` in ~90 places, which
made it impossible to use Memory Tool inside an Obsidian vault (Obsidian hides
dot-prefixed folders). The base folder name is now configurable.

Discovery order
---------------
1. ``MEMORY_TOOL_ROOT`` / ``MEMORY_TOOL_BASE`` environment variables
2. A pointer file (``.memory-tool.yml``) found by walking up from the start
   directory. It holds a single ``base:`` key.
3. Legacy fallback: a ``.memory/`` directory found by walking up.

The pointer file is deliberately tiny and stays at the *project root*, because
the real settings file lives at ``<base>/config.yaml`` -- inside the very folder
whose name we are trying to discover. Reading config to learn the base folder
would be circular, so the pointer breaks that cycle.

A base of ``"."`` means the project root itself *is* the base, so ``m`` writes
to ``./timeline/...`` rather than ``./.memory/timeline/...``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

POINTER_FILENAME = ".memory-tool.yml"
DEFAULT_BASE = ".memory"
ROOT_BASE = "."
CONFIG_FILENAME = "config.yaml"

ENV_ROOT = "MEMORY_TOOL_ROOT"
ENV_BASE = "MEMORY_TOOL_BASE"

#: How many parent directories to examine while searching for the base folder.
#: ``config.py`` used 5 and the planner modules walked to the filesystem root;
#: 10 standardizes both without risking a walk across an entire drive.
MAX_SEARCH_DEPTH = 10

#: Folders holding searchable knowledge. When the base *is* the project root
#: these are the only folders scanned -- without this guard, searching would
#: descend into ``venv/``, ``.git/`` and ``node_modules/``.
CONTENT_SUBDIRS: Tuple[str, ...] = (
    "timeline",
    "modules",
    "concepts",
    "plans",
    "reviews",
    "summaries",
    "docs",
)

#: Generated caches and indexes. These live in the base folder and must be
#: carried along by a rename, but are never search targets.
STATE_ENTRIES: Tuple[str, ...] = (
    "cache",
    ".cache",
    ".index",
    ".embeddings",
    ".connections.db",
    ".index.db",
    ".path_check_cache.json",
    ".suggestion_cache.json",
)

#: Directory name for the *global*, cross-project cache under the user's home
#: directory (``~/.memory/.cache/``). This is deliberately independent of the
#: per-project base folder: renaming a project's base must never move or
#: invalidate the shared cache, so this constant is not configurable.
GLOBAL_CACHE_DIRNAME = ".memory"

#: Names that must never become the base folder, because moving the knowledge
#: base on top of them would destroy unrelated data.
RESERVED_BASE_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".claude",
        ".obsidian",
        "venv",
        ".venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        "site-packages",
    }
)


class InvalidBaseNameError(ValueError):
    """Raised when a base folder name is unusable or unsafe."""


# --------------------------------------------------------------------------
# Name validation
# --------------------------------------------------------------------------


def validate_base_name(name: str) -> str:
    """Normalize and validate a base folder name.

    Args:
        name: Candidate name, e.g. ``"memory"``, ``".memory"``, ``"."``, ``"./"``

    Returns:
        Normalized name -- either ``"."`` or a single path segment.

    Raises:
        InvalidBaseNameError: If the name is empty, absolute, contains a path
            separator or ``..``, or collides with a reserved directory.
    """
    if name is None:
        raise InvalidBaseNameError("Base folder name cannot be None")

    raw = str(name).strip()
    if not raw:
        raise InvalidBaseNameError("Base folder name cannot be empty")

    # Accept the several spellings users reach for when they mean "project root"
    if raw in {".", "./", ".\\", "", "/", "\\"}:
        return ROOT_BASE

    # Strip a leading "./" so "./memory" is treated as "memory"
    if raw.startswith("./") or raw.startswith(".\\"):
        raw = raw[2:].strip()
        if not raw:
            return ROOT_BASE

    normalized = raw.replace("\\", "/").rstrip("/")
    if not normalized:
        return ROOT_BASE

    if ".." in Path(normalized).parts:
        raise InvalidBaseNameError(
            f"Base folder name cannot contain '..': {name!r}"
        )

    if Path(normalized).is_absolute() or normalized.startswith("/"):
        raise InvalidBaseNameError(
            f"Base folder must be a name relative to the project root, "
            f"not an absolute path: {name!r}"
        )

    # Windows drive-letter form ("C:memory")
    if len(normalized) >= 2 and normalized[1] == ":":
        raise InvalidBaseNameError(
            f"Base folder must be a name relative to the project root, "
            f"not an absolute path: {name!r}"
        )

    if "/" in normalized:
        raise InvalidBaseNameError(
            f"Base folder must be a single folder name, not a nested path: {name!r}"
        )

    if normalized.startswith("-"):
        raise InvalidBaseNameError(
            f"Base folder name cannot start with '-': {name!r}"
        )

    if normalized.lower() in RESERVED_BASE_NAMES:
        raise InvalidBaseNameError(
            f"'{normalized}' is reserved and cannot be used as the base folder"
        )

    return normalized


# --------------------------------------------------------------------------
# Pointer file I/O
# --------------------------------------------------------------------------


def pointer_path_for(root: Path) -> Path:
    """Return the pointer file path for a project root."""
    return Path(root) / POINTER_FILENAME


def read_pointer(root: Path) -> Optional[str]:
    """Read the base folder name from a project root's pointer file.

    Args:
        root: Project root directory

    Returns:
        Normalized base name, or None if there is no readable pointer.
    """
    pointer = pointer_path_for(root)
    if not pointer.is_file():
        return None

    try:
        data = yaml.safe_load(pointer.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None

    if not isinstance(data, dict):
        return None

    base = data.get("base")
    if base is None:
        return None

    try:
        return validate_base_name(base)
    except InvalidBaseNameError:
        return None


def write_pointer(root: Path, base_name: str) -> Path:
    """Write the pointer file declaring the base folder name.

    Args:
        root: Project root directory
        base_name: Base folder name (validated before writing)

    Returns:
        Path to the written pointer file.
    """
    normalized = validate_base_name(base_name)
    pointer = pointer_path_for(root)

    content = (
        "# Memory Tool base folder pointer.\n"
        "# 'base' is the folder holding timeline/, modules/, concepts/ and\n"
        '# config.yaml. Use "." to make the project root itself the base.\n'
        "# Change it with: mbase set <name>\n"
        f'base: "{normalized}"\n'
    )
    pointer.write_text(content, encoding="utf-8")
    return pointer


# --------------------------------------------------------------------------
# Resolved paths
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryPaths:
    """Resolved locations for one project.

    Attributes:
        root: Project root (where the pointer file and .gitignore live)
        base: The knowledge base folder itself
        base_name: Base folder name relative to root ("." when base == root)
        found: True if an existing base was discovered, False if this is a
            best-guess default for an uninitialized project
        source: How the base was determined -- "env", "pointer", "legacy" or
            "default". Useful for `mbase show` and for debugging.
    """

    root: Path
    base: Path
    base_name: str
    found: bool
    source: str

    # -- derived content locations -------------------------------------

    @property
    def timeline(self) -> Path:
        return self.base / "timeline"

    @property
    def modules(self) -> Path:
        return self.base / "modules"

    @property
    def concepts(self) -> Path:
        return self.base / "concepts"

    @property
    def plans(self) -> Path:
        return self.base / "plans"

    @property
    def reviews(self) -> Path:
        return self.base / "reviews"

    @property
    def summaries(self) -> Path:
        return self.base / "summaries"

    @property
    def docs(self) -> Path:
        return self.base / "docs"

    @property
    def config_file(self) -> Path:
        return self.base / CONFIG_FILENAME

    @property
    def pointer_file(self) -> Path:
        return pointer_path_for(self.root)

    # -- flags ---------------------------------------------------------

    @property
    def is_root_base(self) -> bool:
        """True when the project root itself is the base folder."""
        return self.base_name == ROOT_BASE

    @property
    def is_hidden_base(self) -> bool:
        """True when the base folder is dot-prefixed (hidden in Obsidian)."""
        return not self.is_root_base and self.base_name.startswith(".")

    def exists(self) -> bool:
        """True if the base folder exists on disk."""
        return self.base.is_dir()

    # -- scan targets --------------------------------------------------

    def search_roots(self) -> List[Path]:
        """Directories to scan for knowledge content.

        When the base is the project root, only the known content subfolders
        are returned -- scanning the root directly would pull in ``venv/``,
        ``.git/``, ``node_modules/`` and every unrelated source folder.

        Returns:
            Existing directories to search, most-specific first.
        """
        if not self.is_root_base:
            return [self.base] if self.base.is_dir() else []

        return [
            self.base / name
            for name in CONTENT_SUBDIRS
            if (self.base / name).is_dir()
        ]

    def movable_entries(self) -> List[Path]:
        """Base-folder entries a rename must carry along.

        Only content subfolders, generated state and ``config.yaml`` are
        included. Anything else in the folder is left alone, which matters
        when the base is the project root and the folder also holds unrelated
        project files.

        Returns:
            Existing paths inside the base folder.
        """
        names = list(CONTENT_SUBDIRS) + list(STATE_ENTRIES) + [CONFIG_FILENAME]
        return [self.base / name for name in names if (self.base / name).exists()]


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------


def base_dir_for_root(root: Path) -> Path:
    """Return the base folder for an explicitly known project root.

    This is the pointer-aware replacement for the old ``root / ".memory"``
    expression. It does not walk up the tree -- the caller has already
    decided which directory is the project root.

    Args:
        root: Project root directory

    Returns:
        Path to the base folder (equal to ``root`` when base is ``"."``).
    """
    root = Path(root)

    env_base = os.environ.get(ENV_BASE)
    env_root = os.environ.get(ENV_ROOT)
    if env_base and (not env_root or Path(env_root) == root):
        try:
            name = validate_base_name(env_base)
        except InvalidBaseNameError:
            name = None
        if name is not None:
            return root if name == ROOT_BASE else root / name

    name = read_pointer(root)
    if name is None:
        return root / DEFAULT_BASE
    return root if name == ROOT_BASE else root / name


def _looks_initialized(path: Path) -> bool:
    """True if `path` looks like a real, initialized knowledge base folder.

    Requires both ``config.yaml`` and ``timeline/``. ``config.yaml`` alone is far
    too common in ordinary projects to be a reliable marker.
    """
    return (path / CONFIG_FILENAME).is_file() and (path / "timeline").is_dir()


def _is_nested_artifact(parent: Path, candidate: Path) -> bool:
    """Detect a nested duplicate base folder left by the old double-append bug.

    Older versions built paths as ``Path.cwd() / ".memory"`` with no upward
    search. Running a command from *inside* the base folder therefore created
    ``<base>/.memory/`` and recorded into it. Because the resolver walks upward,
    that leftover folder would be found first and keep hijacking every command.

    The signature is unambiguous: the artifact is created purely by recording, so
    it only ever contains ``timeline/`` and never a ``config.yaml``, while its
    parent is a fully initialized base folder.

    Args:
        parent: Directory being examined during the upward walk
        candidate: The ``parent/.memory`` directory found there

    Returns:
        True if `candidate` is an artifact and `parent` is the real base.
    """
    if (candidate / CONFIG_FILENAME).is_file():
        return False  # a real, configured base of its own
    return _looks_initialized(parent)


def _candidate_roots(start: Path) -> List[Path]:
    """Yield `start` and its parents, up to MAX_SEARCH_DEPTH."""
    roots = []
    current = Path(start).resolve()
    for _ in range(MAX_SEARCH_DEPTH):
        roots.append(current)
        if current.parent == current:
            break
        current = current.parent
    return roots


def _resolve_from_env(start: Path) -> Optional[MemoryPaths]:
    """Resolve paths from environment variables, if they are set."""
    env_root = os.environ.get(ENV_ROOT)
    env_base = os.environ.get(ENV_BASE)

    if not env_root and not env_base:
        return None

    # Explicit root wins; base name comes from env, else the pointer, else default
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if env_base:
            name = validate_base_name(env_base)
        else:
            name = read_pointer(root) or DEFAULT_BASE
        base = root if name == ROOT_BASE else root / name
        return MemoryPaths(
            root=root, base=base, base_name=name, found=base.is_dir(), source="env"
        )

    # Only MEMORY_TOOL_BASE set. An absolute value names the base folder
    # directly; a bare name is searched for while walking up.
    candidate = Path(env_base).expanduser()
    if candidate.is_absolute():
        base = candidate.resolve()
        return MemoryPaths(
            root=base.parent,
            base=base,
            base_name=base.name,
            found=base.is_dir(),
            source="env",
        )

    name = validate_base_name(env_base)
    for root in _candidate_roots(start):
        base = root if name == ROOT_BASE else root / name
        if base.is_dir():
            return MemoryPaths(
                root=root, base=base, base_name=name, found=True, source="env"
            )

    root = Path(start).resolve()
    base = root if name == ROOT_BASE else root / name
    return MemoryPaths(
        root=root, base=base, base_name=name, found=False, source="env"
    )


def resolve_base(start: Optional[Path] = None) -> MemoryPaths:
    """Resolve the project root and base folder.

    Args:
        start: Directory to start searching from (defaults to cwd)

    Returns:
        MemoryPaths. When nothing is found, ``found`` is False and the paths
        point at the default location so callers can report a helpful error
        or initialize there.
    """
    start_path = Path(start) if start is not None else Path.cwd()

    from_env = _resolve_from_env(start_path)
    if from_env is not None:
        return from_env

    for root in _candidate_roots(start_path):
        # Pointer file first: it is the explicit declaration.
        name = read_pointer(root)
        if name is not None:
            base = root if name == ROOT_BASE else root / name
            return MemoryPaths(
                root=root,
                base=base,
                base_name=name,
                found=base.is_dir(),
                source="pointer",
            )

        # Legacy: an unmarked .memory/ directory from before this was configurable.
        legacy = root / DEFAULT_BASE
        if legacy.is_dir():
            # Don't be hijacked by a nested duplicate left by the old
            # double-append bug -- prefer the real base folder that contains it.
            if _is_nested_artifact(root, legacy):
                return MemoryPaths(
                    root=root.parent,
                    base=root,
                    base_name=root.name,
                    found=True,
                    source="nested-artifact",
                )
            return MemoryPaths(
                root=root,
                base=legacy,
                base_name=DEFAULT_BASE,
                found=True,
                source="legacy",
            )

    # Nothing found -- default location under the starting directory.
    root = start_path.resolve()
    return MemoryPaths(
        root=root,
        base=root / DEFAULT_BASE,
        base_name=DEFAULT_BASE,
        found=False,
        source="default",
    )


# --------------------------------------------------------------------------
# Cached accessor
# --------------------------------------------------------------------------

_cache: dict = {}


def get_paths(start: Optional[Path] = None, refresh: bool = False) -> MemoryPaths:
    """Resolve paths, caching per starting directory.

    Args:
        start: Directory to start searching from (defaults to cwd)
        refresh: Bypass and refresh the cache

    Returns:
        Resolved MemoryPaths.
    """
    key = str(Path(start).resolve()) if start is not None else str(Path.cwd())

    if refresh or key not in _cache:
        _cache[key] = resolve_base(start)
    return _cache[key]


def clear_cache() -> None:
    """Clear the resolution cache (needed after a rename, and in tests)."""
    _cache.clear()


def display_path(path: Path, start: Optional[Path] = None) -> str:
    """Render a path for human-readable output, never raising.

    Because the base folder is now found by walking *up* from the working
    directory, a knowledge-base file is often not inside the working directory.
    A bare ``path.relative_to(Path.cwd())`` raises ValueError in that case, so
    this tries the most useful anchor first and always falls back to something
    printable.

    Args:
        path: Path to render
        start: Directory to resolve the project root from (defaults to cwd)

    Returns:
        A relative path string when the path sits under the working directory
        or the project root, otherwise the absolute path.
    """
    path = Path(path)

    anchors = []
    try:
        anchors.append(Path.cwd())
    except OSError:  # pragma: no cover - cwd deleted underneath us
        pass
    try:
        anchors.append(get_paths(start).root)
    except Exception:  # pragma: no cover - never let display break a command
        pass

    for anchor in anchors:
        try:
            return str(path.relative_to(anchor))
        except ValueError:
            continue

    return str(path)


def get_base_path(start: Optional[Path] = None) -> Path:
    """Convenience accessor for just the base folder path."""
    return get_paths(start).base


def get_project_root(start: Optional[Path] = None) -> Path:
    """Convenience accessor for just the project root path."""
    return get_paths(start).root
