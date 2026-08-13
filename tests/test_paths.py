"""Tests for base folder resolution (memory_tool.utils.paths).

These guard the migration away from ~90 hardcoded ``.memory`` literals.
Every test works in a tmp_path sandbox and clears both the resolution cache
and the environment overrides, so ordering never matters.
"""

import os

import pytest
import yaml

from memory_tool.utils.paths import (
    CONTENT_SUBDIRS,
    DEFAULT_BASE,
    ENV_BASE,
    ENV_ROOT,
    MAX_SEARCH_DEPTH,
    POINTER_FILENAME,
    ROOT_BASE,
    InvalidBaseNameError,
    base_dir_for_root,
    clear_cache,
    get_paths,
    read_pointer,
    resolve_base,
    validate_base_name,
    write_pointer,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Isolate every test from ambient env vars and the resolution cache."""
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def make_project(root, base_name=None, subdirs=("timeline", "modules")):
    """Create a project skeleton. base_name=None means no pointer file."""
    root.mkdir(parents=True, exist_ok=True)

    if base_name is None:
        base = root / DEFAULT_BASE
    else:
        write_pointer(root, base_name)
        base = root if base_name == ROOT_BASE else root / base_name

    base.mkdir(parents=True, exist_ok=True)
    for sub in subdirs:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def isolated_dir(tmp_path):
    """A start directory whose ancestors are all inside tmp_path.

    Resolution walks up to MAX_SEARCH_DEPTH parents, so a shallow tmp_path can
    escape into the real filesystem and find an unrelated knowledge base (a
    developer with ``~/.memory`` would otherwise see spurious failures). Nesting
    past the depth cap contains the walk.
    """
    deep = tmp_path
    for i in range(MAX_SEARCH_DEPTH + 1):
        deep = deep / f"lvl{i}"
    deep.mkdir(parents=True, exist_ok=True)
    return deep


# ---------------------------------------------------------------------------
# validate_base_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("memory", "memory"),
        (".memory", ".memory"),
        ("  memory  ", "memory"),
        ("Memory", "Memory"),
        ("knowledge-base", "knowledge-base"),
        ("memory/", "memory"),
        ("./memory", "memory"),
        (".\\memory", "memory"),
    ],
)
def test_validate_accepts_plain_names(raw, expected):
    assert validate_base_name(raw) == expected


@pytest.mark.parametrize("raw", [".", "./", ".\\", "/", "\\", " . "])
def test_validate_normalizes_root_spellings(raw):
    """All the ways a user might spell "the project root itself"."""
    assert validate_base_name(raw) == ROOT_BASE


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        "..",
        "../memory",
        "memory/../..",
        "a/b",
        "nested/path",
        "/abs/path",
        "C:memory",
        "C:/memory",
        "-flag",
        ".git",
        "venv",
        "node_modules",
        "NODE_MODULES",
        ".obsidian",
    ],
)
def test_validate_rejects_unsafe_names(raw):
    with pytest.raises(InvalidBaseNameError):
        validate_base_name(raw)


# ---------------------------------------------------------------------------
# Pointer file I/O
# ---------------------------------------------------------------------------


def test_write_then_read_pointer_roundtrip(tmp_path):
    write_pointer(tmp_path, "memory")
    assert read_pointer(tmp_path) == "memory"


def test_write_pointer_is_valid_yaml_with_base_key(tmp_path):
    path = write_pointer(tmp_path, "memory")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["base"] == "memory"


def test_write_pointer_normalizes_root_base(tmp_path):
    write_pointer(tmp_path, "./")
    assert read_pointer(tmp_path) == ROOT_BASE


def test_write_pointer_rejects_unsafe_name(tmp_path):
    with pytest.raises(InvalidBaseNameError):
        write_pointer(tmp_path, "../escape")


def test_read_pointer_missing_file_returns_none(tmp_path):
    assert read_pointer(tmp_path) is None


@pytest.mark.parametrize(
    "content",
    [
        "base: [unclosed",  # malformed YAML
        "just a string",  # not a mapping
        "other_key: value",  # no base key
        "base: ../escape",  # unsafe value
        "",  # empty
    ],
)
def test_read_pointer_tolerates_bad_content(tmp_path, content):
    """A corrupt pointer must fall back, never raise."""
    (tmp_path / POINTER_FILENAME).write_text(content, encoding="utf-8")
    assert read_pointer(tmp_path) is None


# ---------------------------------------------------------------------------
# resolve_base -- pointer discovery
# ---------------------------------------------------------------------------


def test_resolve_finds_pointer_in_start_dir(tmp_path):
    base = make_project(tmp_path, "memory")
    paths = resolve_base(tmp_path)

    assert paths.source == "pointer"
    assert paths.root == tmp_path.resolve()
    assert paths.base == base
    assert paths.base_name == "memory"
    assert paths.found is True


def test_resolve_walks_up_to_find_pointer(tmp_path):
    make_project(tmp_path, "memory")
    deep = tmp_path / "src" / "pkg" / "sub"
    deep.mkdir(parents=True)

    paths = resolve_base(deep)

    assert paths.root == tmp_path.resolve()
    assert paths.base_name == "memory"


def test_resolve_root_base_makes_base_equal_root(tmp_path):
    """base: "." is the Obsidian-vault case the whole feature exists for."""
    make_project(tmp_path, ROOT_BASE)

    paths = resolve_base(tmp_path)

    assert paths.base == tmp_path.resolve()
    assert paths.root == tmp_path.resolve()
    assert paths.is_root_base is True
    assert paths.timeline == tmp_path.resolve() / "timeline"


def test_root_base_timeline_path_has_no_dot_segment(tmp_path):
    """The user-facing goal: ./timeline/... not ./.memory/timeline/..."""
    make_project(tmp_path, ROOT_BASE)
    paths = resolve_base(tmp_path)

    relative = paths.timeline.relative_to(paths.root)
    assert str(relative).replace("\\", "/") == "timeline"


# ---------------------------------------------------------------------------
# resolve_base -- legacy fallback
# ---------------------------------------------------------------------------


def test_resolve_falls_back_to_legacy_memory_dir(tmp_path):
    """Existing projects have no pointer file and must keep working."""
    base = make_project(tmp_path, base_name=None)

    paths = resolve_base(tmp_path)

    assert paths.source == "legacy"
    assert paths.base == base
    assert paths.base_name == DEFAULT_BASE
    assert paths.found is True


def test_pointer_wins_over_legacy_dir_at_same_level(tmp_path):
    """A half-finished migration must not resolve to the stale folder."""
    (tmp_path / DEFAULT_BASE).mkdir()
    (tmp_path / "memory").mkdir()
    write_pointer(tmp_path, "memory")

    paths = resolve_base(tmp_path)

    assert paths.base_name == "memory"
    assert paths.source == "pointer"


def test_nearer_legacy_dir_wins_over_farther_pointer(tmp_path):
    """Per-level checks: the closest project boundary should win."""
    write_pointer(tmp_path, "memory")
    (tmp_path / "memory").mkdir()

    inner = tmp_path / "inner"
    (inner / DEFAULT_BASE).mkdir(parents=True)

    paths = resolve_base(inner)

    assert paths.root == inner.resolve()
    assert paths.source == "legacy"


def test_resolve_not_found_returns_default_without_raising(tmp_path):
    start = isolated_dir(tmp_path)

    paths = resolve_base(start)

    assert paths.found is False
    assert paths.source == "default"
    assert paths.base == start.resolve() / DEFAULT_BASE


def test_resolve_stops_before_walking_entire_drive(tmp_path):
    """MAX_SEARCH_DEPTH keeps a deep cwd from scanning to the filesystem root."""
    start = isolated_dir(tmp_path)
    make_project(tmp_path, "memory")

    paths = resolve_base(start)

    # tmp_path is past the depth cap, so it must not be found
    assert paths.found is False


# ---------------------------------------------------------------------------
# Environment overrides
# ---------------------------------------------------------------------------


def test_env_root_and_base_take_precedence_over_pointer(tmp_path, monkeypatch):
    make_project(tmp_path, "memory")
    override = tmp_path / "override"
    (override / "custom").mkdir(parents=True)

    monkeypatch.setenv(ENV_ROOT, str(override))
    monkeypatch.setenv(ENV_BASE, "custom")

    paths = resolve_base(tmp_path)

    assert paths.source == "env"
    assert paths.root == override.resolve()
    assert paths.base == override.resolve() / "custom"


def test_env_root_alone_reads_pointer_from_that_root(tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    make_project(other, "memory")

    monkeypatch.setenv(ENV_ROOT, str(other))
    paths = resolve_base(tmp_path)

    assert paths.root == other.resolve()
    assert paths.base_name == "memory"


def test_env_root_alone_without_pointer_uses_default(tmp_path, monkeypatch):
    other = tmp_path / "other"
    (other / DEFAULT_BASE).mkdir(parents=True)

    monkeypatch.setenv(ENV_ROOT, str(other))
    paths = resolve_base(tmp_path)

    assert paths.base_name == DEFAULT_BASE


def test_env_base_absolute_path_names_the_base_directly(tmp_path, monkeypatch):
    base = tmp_path / "elsewhere" / "kb"
    base.mkdir(parents=True)

    monkeypatch.setenv(ENV_BASE, str(base))
    paths = resolve_base(tmp_path)

    assert paths.source == "env"
    assert paths.base == base.resolve()
    assert paths.root == base.resolve().parent


def test_env_base_relative_name_is_searched_upward(tmp_path, monkeypatch):
    (tmp_path / "custom").mkdir()
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)

    monkeypatch.setenv(ENV_BASE, "custom")
    paths = resolve_base(deep)

    assert paths.root == tmp_path.resolve()
    assert paths.base == tmp_path.resolve() / "custom"


def test_env_base_root_spelling_resolves_to_root(tmp_path, monkeypatch):
    (tmp_path / "timeline").mkdir()
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    monkeypatch.setenv(ENV_BASE, ".")

    paths = resolve_base(tmp_path)

    assert paths.is_root_base is True
    assert paths.base == tmp_path.resolve()


def test_env_base_unsafe_value_raises(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    monkeypatch.setenv(ENV_BASE, "../escape")

    with pytest.raises(InvalidBaseNameError):
        resolve_base(tmp_path)


# ---------------------------------------------------------------------------
# base_dir_for_root -- the convention-A replacement
# ---------------------------------------------------------------------------


def test_base_dir_for_root_reads_pointer(tmp_path):
    write_pointer(tmp_path, "memory")
    assert base_dir_for_root(tmp_path) == tmp_path / "memory"


def test_base_dir_for_root_returns_root_for_root_base(tmp_path):
    write_pointer(tmp_path, ROOT_BASE)
    assert base_dir_for_root(tmp_path) == tmp_path


def test_base_dir_for_root_defaults_without_pointer(tmp_path):
    """Preserves the old `root / ".memory"` behaviour for legacy projects."""
    assert base_dir_for_root(tmp_path) == tmp_path / DEFAULT_BASE


def test_base_dir_for_root_does_not_walk_up(tmp_path):
    """The caller already decided the root; don't second-guess it."""
    write_pointer(tmp_path, "memory")
    child = tmp_path / "child"
    child.mkdir()

    assert base_dir_for_root(child) == child / DEFAULT_BASE


def test_base_dir_for_root_honours_env_base(tmp_path, monkeypatch):
    write_pointer(tmp_path, "memory")
    monkeypatch.setenv(ENV_BASE, "custom")

    assert base_dir_for_root(tmp_path) == tmp_path / "custom"


def test_base_dir_for_root_ignores_env_base_for_other_roots(tmp_path, monkeypatch):
    """An env override scoped to one root must not leak into another."""
    other = tmp_path / "other"
    other.mkdir()
    write_pointer(other, "memory")

    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    monkeypatch.setenv(ENV_BASE, "custom")

    assert base_dir_for_root(other) == other / "memory"


# ---------------------------------------------------------------------------
# search_roots -- the base==root guardrail
# ---------------------------------------------------------------------------


def test_search_roots_is_just_base_when_not_root_base(tmp_path):
    make_project(tmp_path, "memory")
    paths = resolve_base(tmp_path)

    assert paths.search_roots() == [paths.base]


def test_search_roots_excludes_unrelated_folders_for_root_base(tmp_path):
    """The whole point: never scan venv/, .git/, node_modules/ or src/."""
    make_project(tmp_path, ROOT_BASE, subdirs=("timeline", "modules", "concepts"))
    for noise in ("venv", ".git", "node_modules", "src", "__pycache__"):
        (tmp_path / noise).mkdir(exist_ok=True)

    paths = resolve_base(tmp_path)
    names = {p.name for p in paths.search_roots()}

    assert names == {"timeline", "modules", "concepts"}
    assert not names & {"venv", ".git", "node_modules", "src", "__pycache__"}


def test_search_roots_only_lists_existing_dirs(tmp_path):
    make_project(tmp_path, ROOT_BASE, subdirs=("timeline",))
    paths = resolve_base(tmp_path)

    assert [p.name for p in paths.search_roots()] == ["timeline"]


def test_search_roots_empty_when_base_missing(tmp_path):
    paths = resolve_base(isolated_dir(tmp_path))
    assert paths.search_roots() == []


def test_content_subdirs_are_all_reachable_as_properties(tmp_path):
    """Guards against a subdir being added to the tuple but not the dataclass."""
    make_project(tmp_path, "memory", subdirs=CONTENT_SUBDIRS)
    paths = resolve_base(tmp_path)

    for name in CONTENT_SUBDIRS:
        assert getattr(paths, name) == paths.base / name


# ---------------------------------------------------------------------------
# movable_entries -- the rename safety guarantee
# ---------------------------------------------------------------------------


def test_movable_entries_includes_content_state_and_config(tmp_path):
    base = make_project(tmp_path, "memory", subdirs=("timeline", "modules"))
    (base / "config.yaml").write_text("version: '1.0'", encoding="utf-8")
    (base / ".connections.db").write_text("", encoding="utf-8")
    (base / ".embeddings").mkdir()

    names = {p.name for p in resolve_base(tmp_path).movable_entries()}

    assert {"timeline", "modules", "config.yaml", ".connections.db", ".embeddings"} <= names


def test_movable_entries_leaves_unrelated_files_alone(tmp_path):
    """Critical for base=".": a rename must not drag off project source."""
    make_project(tmp_path, ROOT_BASE, subdirs=("timeline", "modules"))
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("hi", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")

    names = {p.name for p in resolve_base(tmp_path).movable_entries()}

    assert names == {"timeline", "modules"}
    assert not names & {"src", "README.md", "pyproject.toml"}


# ---------------------------------------------------------------------------
# Flags and caching
# ---------------------------------------------------------------------------


def test_is_hidden_base_flags_dot_prefixed_only(tmp_path):
    make_project(tmp_path, ".memory")
    assert resolve_base(tmp_path).is_hidden_base is True

    clear_cache()
    other = tmp_path / "visible"
    make_project(other, "memory")
    assert resolve_base(other).is_hidden_base is False


def test_root_base_is_not_reported_as_hidden(tmp_path):
    make_project(tmp_path, ROOT_BASE)
    paths = resolve_base(tmp_path)

    assert paths.is_root_base is True
    assert paths.is_hidden_base is False


def test_get_paths_caches_by_start_dir(tmp_path):
    make_project(tmp_path, "memory")
    first = get_paths(tmp_path)

    write_pointer(tmp_path, "renamed")
    assert get_paths(tmp_path) is first  # cached

    assert get_paths(tmp_path, refresh=True).base_name == "renamed"


def test_clear_cache_forces_reresolution(tmp_path):
    make_project(tmp_path, "memory")
    assert get_paths(tmp_path).base_name == "memory"

    write_pointer(tmp_path, "renamed")
    clear_cache()

    assert get_paths(tmp_path).base_name == "renamed"


def test_exists_reflects_disk_state(tmp_path):
    write_pointer(tmp_path, "memory")
    assert resolve_base(tmp_path).exists() is False

    (tmp_path / "memory").mkdir()
    clear_cache()
    assert resolve_base(tmp_path).exists() is True


# ---------------------------------------------------------------------------
# Nested-artifact guard (the .memory/.memory double-append bug)
# ---------------------------------------------------------------------------


def make_initialized_base(base):
    """A base folder complete enough to be recognized as initialized."""
    base.mkdir(parents=True, exist_ok=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (base / "timeline").mkdir(exist_ok=True)
    (base / "modules").mkdir(exist_ok=True)
    return base


def make_nested_artifact(base):
    """Reproduce what the old `Path.cwd() / '.memory'` bug created."""
    stray = base / DEFAULT_BASE / "timeline" / "daily" / "2026-08"
    stray.mkdir(parents=True, exist_ok=True)
    (stray / "13.md").write_text("- 00:31 | recorded into the wrong place", encoding="utf-8")
    return base / DEFAULT_BASE


def test_nested_artifact_does_not_hijack_resolution(tmp_path):
    """Running from inside the base folder must resolve to the base, not the stray.

    This is the Obsidian case: the plugin sets cwd to the vault root, which is
    the base folder itself.
    """
    base = make_initialized_base(tmp_path / DEFAULT_BASE)
    make_nested_artifact(base)

    paths = resolve_base(base)

    assert paths.base == base.resolve()
    assert paths.root == tmp_path.resolve()
    assert paths.source == "nested-artifact"
    assert paths.timeline == base.resolve() / "timeline"


def test_nested_artifact_guard_works_for_a_visible_base_too(tmp_path):
    base = make_initialized_base(tmp_path / "memory")
    make_nested_artifact(base)

    paths = resolve_base(base)

    assert paths.base == base.resolve()
    assert paths.base_name == "memory"


def test_real_nested_base_with_config_is_respected(tmp_path):
    """A genuine .memory/ that has its own config.yaml is not an artifact."""
    outer = make_initialized_base(tmp_path / DEFAULT_BASE)
    inner = make_initialized_base(outer / DEFAULT_BASE)

    paths = resolve_base(outer)

    assert paths.base == inner.resolve()
    assert paths.source == "legacy"


def test_project_with_unrelated_config_yaml_is_not_mistaken_for_a_base(tmp_path):
    """config.yaml alone must not make a project root look initialized."""
    (tmp_path / "config.yaml").write_text("my_app: true", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    base = tmp_path / DEFAULT_BASE
    (base / "timeline").mkdir(parents=True)

    paths = resolve_base(tmp_path)

    assert paths.base == base.resolve()
    assert paths.source == "legacy"


def test_pointer_file_still_wins_over_nested_artifact(tmp_path):
    base = make_initialized_base(tmp_path / "memory")
    make_nested_artifact(base)
    write_pointer(tmp_path, "memory")

    paths = resolve_base(tmp_path)

    assert paths.base == base
    assert paths.source == "pointer"


def test_normal_project_resolution_is_unaffected_by_the_guard(tmp_path):
    """No stray folder: the ordinary upward walk must behave exactly as before."""
    base = make_initialized_base(tmp_path / DEFAULT_BASE)

    from_root = resolve_base(tmp_path)
    assert from_root.base == base.resolve()
    assert from_root.source == "legacy"

    clear_cache()
    from_inside = resolve_base(base)
    assert from_inside.base == base.resolve()
    assert from_inside.root == tmp_path.resolve()
