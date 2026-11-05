"""Tests for the document format: frontmatter and a title, in one file.

A document starts as one file and moves into a folder of its own name when it
gets a child. Every command that takes a module has to handle both places.
"""

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.context.related_files import get_module_related_files
from memory_tool.core.connections import ConnectionGraph, ConnectionParser
from memory_tool.core.federation import Publisher
from memory_tool.core.module import ModuleManager
from memory_tool.utils.frontmatter import Frontmatter
from memory_tool.utils.path_checker import PathChecker
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    base = tmp_path / ".memory"
    (base / "modules").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield tmp_path
    clear_cache()


@pytest.fixture
def manager(project):
    return ModuleManager(project)


@pytest.fixture
def modules(manager):
    return manager.modules_path


def tree(modules):
    return sorted(p.relative_to(modules).as_posix() for p in modules.rglob("*.md"))


def write(modules, relative, text="# doc\n"):
    path = modules / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- the document ------------------------------------------------------------


def test_new_document_is_one_flat_file(manager, modules):
    path = manager.create("topic")

    assert path == modules / "topic.md"
    assert tree(modules) == ["topic.md"]


def test_new_document_holds_only_frontmatter_and_a_title(manager):
    content = manager.create("topic").read_text(encoding="utf-8")
    metadata, body = Frontmatter.parse(content)

    assert body.strip() == "# topic"
    assert set(metadata) == {"type", "description", "tags", "generated"}
    assert "<!--" not in content
    assert metadata["generated"]["by"].startswith("human:")
    assert metadata["generated"]["at"]


def test_values_are_written_to_the_frontmatter(manager):
    path = manager.create(
        "topic",
        description="왜: 콜론이 있는 설명",
        tags=["예시", "a: b"],
        doc_type="판단",
        generated_by="claude/5",
    )
    metadata, _ = Frontmatter.parse(path.read_text(encoding="utf-8"))

    assert metadata["type"] == "판단"
    assert metadata["description"] == "왜: 콜론이 있는 설명"
    assert metadata["tags"] == ["예시", "a: b"]
    assert metadata["generated"]["by"] == "claude/5"


def test_an_unknown_type_is_not_refused(manager):
    metadata, _ = Frontmatter.parse(
        manager.create("topic", doc_type="회고").read_text(encoding="utf-8")
    )

    assert metadata["type"] == "회고"


def test_a_document_created_where_a_folder_exists_goes_inside_it(manager, modules):
    write(modules, "group/child.md")

    assert manager.create("group") == modules / "group" / "group.md"


def test_a_document_without_type_or_frontmatter_is_still_a_module(manager, modules):
    write(modules, "plain.md", "# plain\n\nno frontmatter\n")
    write(modules, "unknown.md", "---\ncustom_key: 1\n---\n# unknown\n")

    assert manager.resolve_module_doc("plain") is not None
    assert manager.resolve_module_doc("unknown") is not None
    assert get_module_related_files(modules / "unknown").is_empty()


def test_new_fields_coexist_with_published_metadata(modules):
    text = (
        "---\nversion: 3\nsource_hash: abc\ntype: 참고\nsources:\n  - id: a\n"
        "    resource: src/a.py\n---\n# doc\n"
    )
    updated = Frontmatter.inject(text, {"version": 4})
    metadata, body = Frontmatter.parse(updated)

    assert metadata["version"] == 4
    assert metadata["type"] == "참고"
    assert metadata["sources"][0]["resource"] == "src/a.py"
    assert body.strip() == "# doc"


# --- children ----------------------------------------------------------------


def test_a_first_child_moves_the_parent_into_its_folder(manager, modules):
    parent = manager.create("topic")
    parent.write_text(parent.read_text(encoding="utf-8") + "\nkept body\n", encoding="utf-8")

    manager.create("topic/child")

    assert tree(modules) == ["topic/child.md", "topic/topic.md"]
    assert "kept body" in (modules / "topic" / "topic.md").read_text(encoding="utf-8")


def test_the_parent_keeps_its_name_after_moving(manager):
    manager.create("topic")
    manager.create("topic/child")

    assert manager.resolve_module_doc("topic") is not None
    assert [p.as_posix() for p in manager.discover_all_modules()] == ["topic", "topic/child"]


def test_wiki_links_to_the_parent_survive_the_move(manager, modules):
    manager.create("topic")
    other = manager.create("other")
    other.write_text(other.read_text(encoding="utf-8") + "\n[[topic]]\n", encoding="utf-8")

    manager.create("topic/child")

    connections = ConnectionParser.parse_module(modules / "other", "other")
    assert [c.target for c in connections] == ["topic"]
    assert manager.resolve_module_doc("topic").name == "topic.md"


def test_a_second_child_moves_nothing(manager, modules):
    manager.create("topic")
    manager.create("topic/first")

    assert manager.documents_moved_by_creating("topic/second") == []

    manager.create("topic/second")

    assert tree(modules) == ["topic/first.md", "topic/second.md", "topic/topic.md"]


def test_a_child_makes_every_flat_ancestor_move(manager, modules):
    write(modules, "a.md")
    write(modules, "a/b.md")

    manager.create("a/b/c")

    assert tree(modules) == ["a/a.md", "a/b/b.md", "a/b/c.md"]


def test_a_child_in_a_plain_folder_moves_nothing(manager, modules):
    manager.create("group/child")

    assert tree(modules) == ["group/child.md"]


def test_a_side_by_side_document_made_by_hand_is_read_and_moved_on_the_next_child(manager, modules):
    write(modules, "topic.md", "parent")
    write(modules, "topic/child.md", "child")

    assert manager.resolve_module_doc("topic") == modules / "topic.md"

    manager.create("topic/second")

    assert tree(modules) == ["topic/child.md", "topic/second.md", "topic/topic.md"]


def test_a_legacy_template_request_keeps_its_layout(manager, modules):
    path = manager.create("topic", kind="knowledge", nature="concept")

    assert path == modules / "topic" / "topic.md"
    assert "**Kind:** knowledge" in path.read_text(encoding="utf-8")


# --- the commands ------------------------------------------------------------


def test_create_command(project, modules):
    result = runner.invoke(app, ["module", "create", "topic", "--type", "참고", "--desc", "설명"])

    assert result.exit_code == 0, result.output
    metadata, _ = Frontmatter.parse((modules / "topic.md").read_text(encoding="utf-8"))
    assert metadata["type"] == "참고"
    assert metadata["description"] == "설명"


def test_create_command_reports_a_move(project, modules):
    runner.invoke(app, ["module", "create", "topic"])

    result = runner.invoke(app, ["module", "create", "topic/child"])

    assert result.exit_code == 0, result.output
    assert "Moved" in result.output
    assert "relink" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["module", "create", "old", "--kind", "knowledge"],
        ["module", "create", "old", "--nature", "concept"],
        ["module", "create", "old", "--kind", "knowledge", "--draft"],
    ],
)
def test_retiring_options_still_work_and_warn(project, arguments):
    result = runner.invoke(app, arguments)

    assert result.exit_code == 0, result.output
    assert "will be removed" in result.output
    assert "**Kind:**" in (
        project / ".memory" / "modules" / "old" / "old.md"
    ).read_text(encoding="utf-8")


def test_grow_still_works_and_warns(project):
    runner.invoke(app, ["module", "create", "old", "--kind", "knowledge", "--draft"])

    result = runner.invoke(app, ["module", "grow", "old"])

    assert result.exit_code == 0, result.output
    assert "will be removed" in result.output


def test_a_plain_create_gives_no_warning(project):
    result = runner.invoke(app, ["module", "create", "topic"])

    assert "will be removed" not in result.output


def test_check_links_names_the_broken_target(project, modules):
    write(modules, "topic.md", "[[missing-target]]\n")
    runner.invoke(app, ["module", "rebuild-graph"])

    result = runner.invoke(app, ["module", "check-links"])

    assert "missing-target" in result.output


# --- archive -----------------------------------------------------------------


def test_archive_and_restore_a_flat_document(manager, modules):
    manager.create("topic")

    archived = manager.archive("topic")

    assert archived == modules / "archive" / "topic.md"
    assert not (modules / "topic.md").exists()

    restored = manager.unarchive("topic")

    assert restored == modules / "topic.md"
    assert restored.is_file()


def test_archive_keeps_a_subject_and_its_children_together(manager, modules):
    manager.create("topic")
    manager.create("topic/child")

    manager.archive("topic")

    assert not (modules / "topic").exists()
    assert (modules / "archive" / "topic" / "topic.md").is_file()
    assert (modules / "archive" / "topic" / "child.md").is_file()

    manager.unarchive("topic")

    assert (modules / "topic" / "topic.md").is_file()
    assert (modules / "topic" / "child.md").is_file()


def test_archive_keeps_a_side_by_side_subject_together(manager, modules):
    write(modules, "topic.md", "parent")
    write(modules, "topic/child.md", "child")

    manager.archive("topic")

    assert sorted(p.relative_to(modules).as_posix() for p in modules.rglob("*.md") if p.name != "_index.md") == [
        "archive/topic.md",
        "archive/topic/child.md",
    ]

    manager.unarchive("topic")

    assert tree(modules) == ["archive/_index.md", "topic.md", "topic/child.md"]


def test_archive_of_a_missing_module_is_refused(manager):
    with pytest.raises(Exception, match="not found"):
        manager.archive("missing")


# --- links -------------------------------------------------------------------


def test_links_of_a_flat_document_are_read(modules):
    write(modules, "topic.md", "[[other]]\n")

    connections = ConnectionParser.parse_module(modules / "topic", "topic")

    assert [c.target for c in connections] == ["other"]


def test_links_of_a_child_are_not_attributed_to_the_parent(modules):
    write(modules, "topic/topic.md", "[[from-parent]]\n")
    write(modules, "topic/child.md", "[[from-child]]\n")

    connections = ConnectionParser.parse_module(modules / "topic", "topic")

    assert [c.target for c in connections] == ["from-parent"]


@pytest.mark.parametrize(
    "link, expected",
    [
        ("[text](other.md)", "group/other"),
        ("[text](../outside.md)", "outside"),
        ("[text](../deep/deep.md)", "deep"),
        ("[text](other.md#section)", "group/other"),
        ("[text](two%20words.md)", "group/two words"),
    ],
)
def test_markdown_links_become_module_names(modules, link, expected):
    write(modules, "group/topic.md", link + "\n")

    connections = ConnectionParser.parse_module(modules / "group" / "topic", "group/topic")

    assert [c.target for c in connections] == [expected]


@pytest.mark.parametrize(
    "link",
    [
        "[site](https://example.com/page.md)",
        "![image](picture.md)",
        "[outside](../../../elsewhere.md)",
        "[not a document](notes.txt)",
    ],
)
def test_other_links_are_ignored(modules, link):
    write(modules, "group/topic.md", link + "\n")

    assert ConnectionParser.parse_module(modules / "group" / "topic", "group/topic") == []


def test_wiki_and_markdown_links_are_both_in_the_graph(project, modules):
    write(modules, "topic.md", "[[wiki-target]] and [md](markdown-target.md)\n")

    ConnectionGraph().rebuild_from_modules(modules)

    targets = {c.target for c in ConnectionGraph().get_outgoing_connections("topic")}
    assert targets == {"wiki-target", "markdown-target"}


# --- sources -----------------------------------------------------------------


def test_mcheck_verifies_code_paths_in_sources(project, modules):
    (project / "src").mkdir()
    (project / "src" / "real.py").write_text("x", encoding="utf-8")
    write(
        modules,
        "topic.md",
        "---\nsources:\n"
        "  - id: a\n    resource: src/real.py\n"
        "  - id: b\n    resource: src/missing.py\n"
        "  - id: c\n    resource: https://example.com/spec\n"
        "---\n# topic\n",
    )

    result = PathChecker(project).check_module("topic")

    assert result.has_related_files
    assert result.get_valid_paths() == ["src/real.py"]
    assert result.get_missing_paths() == ["src/missing.py"]


def test_related_files_section_is_still_read_beside_sources(project, modules):
    write(
        modules,
        "topic.md",
        "---\nsources:\n  - resource: src/a.py\n---\n# topic\n\n"
        "## Related Files\n\n- **Source:** `src/b.py`\n",
    )

    paths = get_module_related_files(modules / "topic").all_paths()

    assert "src/a.py" in paths and "src/b.py" in paths


def test_timeline_sources_are_found_in_the_base_folder(project, modules):
    timeline = project / ".memory" / "timeline" / "daily" / "2026-09"
    timeline.mkdir(parents=True)
    (timeline / "2026-09-03.md").write_text("- entry\n", encoding="utf-8")
    write(
        modules,
        "topic.md",
        "---\nsources:\n  - resource: timeline/daily/2026-09/2026-09-03.md\n---\n# topic\n",
    )

    assert PathChecker(project).check_module("topic").get_missing_paths() == []


# --- publishing --------------------------------------------------------------


@pytest.fixture
def publisher(project):
    kb = project.parent / f"{project.name}-kb"
    kb.mkdir()
    subject = Publisher(project / ".memory", kb)
    subject.project_name = "sample"
    return subject, kb


def test_a_flat_document_can_be_published(modules, publisher):
    subject, kb = publisher
    write(modules, "topic.md", "---\ntype: 참고\n---\n# topic\n\nbody\n")

    result = subject.publish("topic")

    assert result["success"], result["message"]
    published = list(kb.rglob("topic.md"))
    assert [p.parent.name for p in published] == ["topic"]

    metadata, body = Frontmatter.parse(published[0].read_text(encoding="utf-8"))
    assert metadata["type"] == "참고"
    assert metadata["origin_project"] == "sample"
    assert "body" in body


def test_publishing_a_subject_carries_children_but_not_plan_md(modules, publisher):
    subject, kb = publisher
    write(modules, "topic/topic.md", "# topic\n")
    write(modules, "topic/child.md", "# child\n")
    write(modules, "topic/PLAN.md", "# plan\n")

    result = subject.publish("topic")

    assert result["success"], result["message"]
    assert sorted(result["files_published"]) == ["child.md", "topic.md"]
    assert not list(kb.rglob("PLAN.md"))
