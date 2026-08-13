"""Tests for the base==root search guardrails.

When the base folder is the project root (``base: "."``), scanning the base
wholesale would pull in ``venv/``, ``.git/``, ``node_modules/`` and unrelated
source files. These tests pin that down at the Searcher level.
"""

import pytest

from memory_tool.core.search import MemorySearcher
from memory_tool.utils.paths import (
    ENV_BASE,
    ENV_ROOT,
    ROOT_BASE,
    clear_cache,
    write_pointer,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def build_vault(root, base_name):
    """Create a project with content plus realistic noise folders."""
    root.mkdir(parents=True, exist_ok=True)
    write_pointer(root, base_name)
    base = root if base_name == ROOT_BASE else root / base_name

    for sub in ("timeline", "modules", "concepts"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (base / "timeline" / "entry.md").write_text(
        "- 10:00 | findable content marker", encoding="utf-8"
    )

    # Noise that must never be scanned
    for noise in ("venv", ".git", "node_modules", "__pycache__", "src"):
        d = root / noise
        d.mkdir(parents=True, exist_ok=True)
        (d / "noise.md").write_text("noise content marker", encoding="utf-8")

    return base


def test_root_base_search_paths_exclude_noise(tmp_path):
    build_vault(tmp_path, ROOT_BASE)
    searcher = MemorySearcher(base_path=tmp_path)

    names = {p.name for p in searcher.get_search_paths(scope="local")}

    assert names == {"timeline", "modules", "concepts"}
    assert not names & {"venv", ".git", "node_modules", "__pycache__", "src"}


def test_root_base_search_paths_never_include_the_root_itself(tmp_path):
    """Returning the root would make every exclusion moot."""
    build_vault(tmp_path, ROOT_BASE)
    searcher = MemorySearcher(base_path=tmp_path)

    paths = searcher.get_search_paths(scope="local")

    assert tmp_path.resolve() not in [p.resolve() for p in paths]


def test_subfolder_base_still_scans_base_wholesale(tmp_path):
    """A real subfolder base is self-contained, so don't over-restrict it."""
    base = build_vault(tmp_path, "memory")
    searcher = MemorySearcher(base_path=tmp_path)

    assert searcher.get_search_paths(scope="local") == [base]


def test_subfolder_base_scan_includes_non_standard_subdirs(tmp_path):
    """Custom folders inside a real base must remain searchable."""
    base = build_vault(tmp_path, "memory")
    (base / "my-custom-notes").mkdir()
    searcher = MemorySearcher(base_path=tmp_path)

    paths = searcher.get_search_paths(scope="local")

    assert paths == [base]  # whole base, so custom folders are covered


def test_root_base_search_paths_empty_when_no_content(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    write_pointer(tmp_path, ROOT_BASE)
    searcher = MemorySearcher(base_path=tmp_path)

    assert searcher.get_search_paths(scope="local") == []


def test_legacy_base_without_pointer_scans_wholesale(tmp_path):
    """Existing .memory/ projects keep their previous search behaviour."""
    base = tmp_path / ".memory"
    (base / "timeline").mkdir(parents=True)
    searcher = MemorySearcher(base_path=tmp_path)

    assert searcher.get_search_paths(scope="local") == [base]
