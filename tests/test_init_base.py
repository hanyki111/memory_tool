"""Tests for `minit --base` and the root-base clobber guard.

With ``--base .`` the knowledge base shares a directory with the project, so
initialization must never write over the project's own README.md, config.yaml
or docs/ folder.
"""

import pytest

from memory_tool.core.init import (
    AlreadyInitializedError,
    InitializationError,
    MemoryInitializer,
)
from memory_tool.utils.paths import (
    DEFAULT_BASE,
    ENV_BASE,
    ENV_ROOT,
    ROOT_BASE,
    clear_cache,
    read_pointer,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Base folder selection
# ---------------------------------------------------------------------------


def test_default_base_is_dot_memory(tmp_path):
    init = MemoryInitializer(tmp_path)
    init.initialize()

    assert (tmp_path / DEFAULT_BASE / "timeline").is_dir()
    assert read_pointer(tmp_path) == DEFAULT_BASE


def test_named_base_creates_visible_folder(tmp_path):
    init = MemoryInitializer(tmp_path, base_name="memory")
    init.initialize()

    assert (tmp_path / "memory" / "timeline").is_dir()
    assert (tmp_path / "memory" / "config.yaml").is_file()
    assert read_pointer(tmp_path) == "memory"


def test_root_base_creates_content_at_top_level(tmp_path):
    init = MemoryInitializer(tmp_path, base_name=".")
    init.initialize()

    assert (tmp_path / "timeline").is_dir()
    assert (tmp_path / "modules").is_dir()
    assert (tmp_path / "config.yaml").is_file()
    assert not (tmp_path / DEFAULT_BASE).exists()
    assert read_pointer(tmp_path) == ROOT_BASE


def test_root_base_structure_has_no_nested_base_dir(tmp_path):
    init = MemoryInitializer(tmp_path, base_name=".")
    structure = init.get_structure()

    assert not any(k.startswith(f"{DEFAULT_BASE}/") for k in structure)
    assert "timeline" in structure
    assert "timeline/.gitkeep" in structure


def test_init_writes_pointer_so_commands_can_find_the_base(tmp_path):
    MemoryInitializer(tmp_path, base_name="knowledge").initialize()

    from memory_tool.utils.paths import resolve_base

    clear_cache()
    paths = resolve_base(tmp_path)
    assert paths.base_name == "knowledge"
    assert paths.source == "pointer"


@pytest.mark.parametrize("bad", ["venv", "../escape", "a/b", ".git", ""])
def test_invalid_base_names_are_refused(tmp_path, bad):
    with pytest.raises(InitializationError):
        MemoryInitializer(tmp_path, base_name=bad)


def test_existing_project_base_name_is_reused(tmp_path):
    """--force and --update-docs must not silently move the base folder."""
    MemoryInitializer(tmp_path, base_name="memory").initialize()
    clear_cache()

    reopened = MemoryInitializer(tmp_path)  # no base_name given

    assert reopened.base_name == "memory"
    assert reopened.memory_path == tmp_path / "memory"


# ---------------------------------------------------------------------------
# Root-base clobber guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["README.md", "config.yaml"])
def test_root_base_refuses_to_overwrite_project_files(tmp_path, name):
    target = tmp_path / name
    target.write_text("PRECIOUS PROJECT CONTENT", encoding="utf-8")

    init = MemoryInitializer(tmp_path, base_name=".")
    with pytest.raises(InitializationError):
        init.initialize()

    assert target.read_text(encoding="utf-8") == "PRECIOUS PROJECT CONTENT"


@pytest.mark.parametrize("name", ["docs", "templates", "modules", "timeline"])
def test_root_base_refuses_to_merge_into_existing_dirs(tmp_path, name):
    d = tmp_path / name
    d.mkdir()
    (d / "existing.md").write_text("project content", encoding="utf-8")

    init = MemoryInitializer(tmp_path, base_name=".")
    with pytest.raises(InitializationError):
        init.initialize()

    assert (d / "existing.md").is_file()


def test_root_base_guard_is_not_bypassed_by_force(tmp_path):
    """--force reinitializes a knowledge base; it does not overwrite a project."""
    readme = tmp_path / "README.md"
    readme.write_text("PRECIOUS", encoding="utf-8")

    init = MemoryInitializer(tmp_path, base_name=".")
    with pytest.raises(InitializationError):
        init.initialize(force=True)

    assert readme.read_text(encoding="utf-8") == "PRECIOUS"


def test_root_base_error_names_the_conflicts(tmp_path):
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    (tmp_path / "docs").mkdir()

    init = MemoryInitializer(tmp_path, base_name=".")
    with pytest.raises(InitializationError) as exc:
        init.initialize()

    message = str(exc.value)
    assert "README.md" in message
    assert "docs" in message


def test_root_base_works_in_an_empty_directory(tmp_path):
    MemoryInitializer(tmp_path, base_name=".").initialize()
    assert (tmp_path / "timeline").is_dir()


def test_unrelated_project_files_do_not_block_root_base(tmp_path):
    """Only the entries we would actually write are conflicts."""
    (tmp_path / "src").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("venv/", encoding="utf-8")

    MemoryInitializer(tmp_path, base_name=".").initialize()

    assert (tmp_path / "timeline").is_dir()
    assert (tmp_path / "src").is_dir()
    assert (tmp_path / "pyproject.toml").is_file()


def test_subfolder_base_is_unaffected_by_project_files(tmp_path):
    """A README only conflicts when the base is the root."""
    (tmp_path / "README.md").write_text("PRECIOUS", encoding="utf-8")

    MemoryInitializer(tmp_path, base_name="memory").initialize()

    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "PRECIOUS"
    assert (tmp_path / "memory" / "README.md").is_file()


# ---------------------------------------------------------------------------
# Re-initialization
# ---------------------------------------------------------------------------


def test_reinit_of_root_base_requires_force(tmp_path):
    MemoryInitializer(tmp_path, base_name=".").initialize()
    clear_cache()

    with pytest.raises(AlreadyInitializedError):
        MemoryInitializer(tmp_path, base_name=".").initialize()


def test_reinit_of_root_base_succeeds_with_force(tmp_path):
    MemoryInitializer(tmp_path, base_name=".").initialize()
    clear_cache()

    MemoryInitializer(tmp_path, base_name=".").initialize(force=True)

    assert (tmp_path / "timeline").is_dir()


def test_project_config_yaml_alone_is_not_treated_as_initialized(tmp_path):
    """config.yaml is too common a filename to be an initialization marker."""
    (tmp_path / "config.yaml").write_text("my_app: true", encoding="utf-8")

    init = MemoryInitializer(tmp_path, base_name=".")

    assert init.is_initialized() is False
