"""Tests for reading and renaming modules in every layout.

AI commands, the TUI and document health each kept their own idea of where a
module's text lives, usually a fixed current.md. On a single-document module
they then reported a large document as empty, or the module as missing.
"""

import pytest

from memory_tool.context.builder import ContextBuilder
from memory_tool.core.module_audit import ModuleAnalyzer
from memory_tool.core.module import ModuleError, ModuleManager
from memory_tool.utils.health_checker import DocumentHealthChecker
from memory_tool.utils.module_docs import (
    discover_module_paths,
    module_documents,
    read_module_text,
    resolve_module_document,
)
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def manager(tmp_path):
    write_pointer(tmp_path, ".memory")
    base = tmp_path / ".memory"
    (base / "modules").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    return ModuleManager(tmp_path)


def write(modules, relative, text="# doc\n"):
    path = modules / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def tree(modules):
    return sorted(p.relative_to(modules).as_posix() for p in modules.rglob("*.md"))


def names(modules, **kwargs):
    return [p.as_posix() for p in discover_module_paths(modules, **kwargs)]


# --- documents ---------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    ["topic/topic.md", "topic.md", "topic/current.md", "topic/module.md"],
)
def test_main_document_is_found_in_every_layout(tmp_path, relative):
    document = write(tmp_path, relative)

    assert resolve_module_document(tmp_path / "topic") == document


def test_side_by_side_parent_is_found_beside_its_folder(tmp_path):
    parent = write(tmp_path, "topic.md")
    write(tmp_path, "topic/child.md")

    assert resolve_module_document(tmp_path / "topic") == parent
    assert module_documents(tmp_path / "topic") == [parent]


def test_children_are_not_part_of_the_parents_documents(tmp_path):
    parent = write(tmp_path, "topic/topic.md")
    write(tmp_path, "topic/child.md")

    assert module_documents(tmp_path / "topic") == [parent]


def test_legacy_documents_are_returned_in_reading_order(tmp_path):
    current = write(tmp_path, "topic/current.md")
    module = write(tmp_path, "topic/module.md")

    assert module_documents(tmp_path / "topic") == [module, current]


def test_legacy_names_limit_what_is_read(tmp_path):
    current = write(tmp_path, "topic/current.md")
    write(tmp_path, "topic/decisions.md")

    assert module_documents(tmp_path / "topic", ("current.md",)) == [current]


def test_a_dot_in_the_module_name_is_not_read_as_a_suffix(tmp_path):
    document = write(tmp_path, "01. basics.md")

    assert resolve_module_document(tmp_path / "01. basics") == document


def test_missing_module_has_no_documents(tmp_path):
    assert resolve_module_document(tmp_path / "missing") is None
    assert module_documents(tmp_path / "missing") == []
    assert read_module_text(tmp_path / "missing") == ""


def test_read_text_labels_files_only_when_there_are_several(tmp_path):
    write(tmp_path, "single.md", "body")
    write(tmp_path, "legacy/module.md", "purpose")
    write(tmp_path, "legacy/current.md", "state")

    assert read_module_text(tmp_path / "single") == "body"
    assert read_module_text(tmp_path / "legacy") == (
        "## module.md\n\npurpose\n\n## current.md\n\nstate"
    )


# --- discovery ---------------------------------------------------------------


def test_discovery_finds_every_layout(tmp_path):
    write(tmp_path, "single/single.md")
    write(tmp_path, "flat.md")
    write(tmp_path, "legacy/current.md")
    write(tmp_path, "group/child.md")

    assert names(tmp_path) == ["flat", "group/child", "legacy", "single"]


def test_plan_md_is_not_a_module(tmp_path):
    write(tmp_path, "topic/topic.md")
    write(tmp_path, "topic/PLAN.md")
    write(tmp_path, "empty/PLAN.md")

    assert names(tmp_path) == ["topic"]


def test_uppercase_topics_stay_modules(tmp_path):
    write(tmp_path, "AI/AI.md")
    write(tmp_path, "MIGRATION-PLAN.md")
    write(tmp_path, "PLAN-release.md")

    assert names(tmp_path) == ["AI", "MIGRATION-PLAN", "PLAN-release"]


def test_archive_is_judged_on_the_relative_path(tmp_path):
    modules = tmp_path / "archive" / "modules"
    write(modules, "topic.md")
    write(modules, "archive/old.md")

    assert names(modules) == ["topic"]
    assert names(modules, include_archived=True) == ["archive/old", "topic"]


def test_manager_uses_the_same_discovery(manager):
    write(manager.modules_path, "topic/topic.md")
    write(manager.modules_path, "topic/PLAN.md")

    assert [p.as_posix() for p in manager.discover_all_modules()] == ["topic"]
    assert manager.list_modules()["active"] == ["topic"]


# --- rename ------------------------------------------------------------------


def test_rename_flat_document(manager):
    write(manager.modules_path, "topic.md", "# topic\n")

    new_path = manager.rename("topic", "subject")

    assert new_path == manager.modules_path / "subject.md"
    assert tree(manager.modules_path) == ["subject.md"]


def test_rename_side_by_side_moves_parent_and_children(manager):
    write(manager.modules_path, "topic.md", "parent")
    write(manager.modules_path, "topic/child/child.md", "child")

    manager.rename("topic", "subject")

    assert tree(manager.modules_path) == ["subject.md", "subject/child/child.md"]
    assert (manager.modules_path / "subject.md").read_text(encoding="utf-8") == "parent"


def test_rename_folder_document_carries_children_and_renames_the_document(manager):
    write(manager.modules_path, "topic/topic.md", "parent")
    write(manager.modules_path, "topic/child.md", "child")

    new_path = manager.rename("topic", "subject")

    assert new_path == manager.modules_path / "subject" / "subject.md"
    assert tree(manager.modules_path) == ["subject/child.md", "subject/subject.md"]
    assert not (manager.modules_path / "topic").exists()


def test_rename_legacy_module_keeps_its_files(manager):
    write(manager.modules_path, "topic/current.md")
    write(manager.modules_path, "topic/module.md")

    new_path = manager.rename("topic", "subject")

    assert new_path == manager.modules_path / "subject"
    assert tree(manager.modules_path) == ["subject/current.md", "subject/module.md"]


def test_rename_into_a_new_parent_folder(manager):
    write(manager.modules_path, "topic.md")

    manager.rename("topic", "group/subject")

    assert tree(manager.modules_path) == ["group/subject.md"]


def test_rename_updates_the_legacy_title(manager):
    write(manager.modules_path, "topic/topic.md", "# Module: topic\n\nbody mentions topic\n")

    new_path = manager.rename("topic", "subject")

    assert new_path.read_text(encoding="utf-8") == "# Module: subject\n\nbody mentions topic\n"


def test_rename_missing_module_is_refused(manager):
    with pytest.raises(ModuleError, match="not found"):
        manager.rename("missing", "subject")


def test_rename_onto_an_existing_module_is_refused(manager):
    write(manager.modules_path, "topic.md")
    write(manager.modules_path, "subject.md")

    with pytest.raises(ModuleError, match="already exists"):
        manager.rename("topic", "subject")

    assert tree(manager.modules_path) == ["subject.md", "topic.md"]


def test_rename_onto_an_existing_folder_is_refused_rather_than_merged(manager):
    write(manager.modules_path, "topic/topic.md")
    write(manager.modules_path, "subject/child.md")

    with pytest.raises(ModuleError, match="already exists"):
        manager.rename("topic", "subject")

    assert tree(manager.modules_path) == ["subject/child.md", "topic/topic.md"]


def test_rename_into_its_own_folder_is_refused(manager):
    write(manager.modules_path, "topic/topic.md")

    with pytest.raises(ModuleError, match="inside itself"):
        manager.rename("topic", "topic/subject")

    assert tree(manager.modules_path) == ["topic/topic.md"]


def test_rename_refuses_when_a_child_already_has_the_new_document_name(manager):
    write(manager.modules_path, "topic/topic.md", "parent")
    write(manager.modules_path, "topic/subject.md", "child")

    with pytest.raises(ModuleError, match="subject.md"):
        manager.rename("topic", "subject")

    assert tree(manager.modules_path) == ["topic/subject.md", "topic/topic.md"]


# --- readers -----------------------------------------------------------------


def test_organizer_measures_a_single_document(tmp_path):
    write(tmp_path, "topic/topic.md", "line\n" * 400)
    write(tmp_path, "flat.md", "line\n" * 10)

    found = {info.name: info for info in ModuleAnalyzer(tmp_path).discover_all_modules()}

    assert set(found) == {"flat", "topic"}
    assert found["topic"].line_count == 400
    assert found["flat"].line_count == 10
    assert "line" in found["topic"].body


def test_organizer_uses_forward_slashes_in_names(tmp_path):
    write(tmp_path, "group/child.md")

    infos = ModuleAnalyzer(tmp_path).discover_all_modules()

    assert [info.name for info in infos] == ["group/child"]


def test_document_health_reports_a_flat_document(manager):
    write(manager.modules_path, "topic.md", "line\n" * 700)

    issues = ContextBuilder(manager.base_path).get_document_health()

    assert [(i["module"], i["file"], i["lines"]) for i in issues] == [("topic", "topic.md", 700)]


def test_document_health_reports_legacy_files_against_their_budgets(manager):
    write(manager.modules_path, "topic/current.md", "line\n" * 250)
    write(manager.modules_path, "topic/decisions.md", "line\n" * 350)

    issues = ContextBuilder(manager.base_path).get_document_health()

    assert sorted(i["file"] for i in issues) == ["current.md", "decisions.md"]


def test_document_health_skips_plan_md_and_archives(manager):
    write(manager.modules_path, "topic/PLAN.md", "line\n" * 700)
    write(manager.modules_path, "archive/old/old.md", "line\n" * 700)

    assert ContextBuilder(manager.base_path).get_document_health() == []


def test_health_checker_skips_plan_md(manager):
    write(manager.modules_path, "topic/topic.md", "line\n" * 2000)
    write(manager.modules_path, "topic/PLAN.md", "line\n" * 2000)

    issues = DocumentHealthChecker(manager.memory_path).check_all_modules()

    assert [issue.module_name for issue in issues] == ["topic"]
