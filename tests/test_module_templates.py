"""Tests for MOP v3.2 module templates (memory_tool.core.module_templates).

Templates are authored as separate documents but modules are stored as a single
file, so the assembly step and its placeholder substitution are what these cover.
"""

import pytest

from memory_tool.core.module import ModuleError, ModuleManager
from memory_tool.core.module_templates import (
    KINDS,
    NATURES,
    TemplateChoice,
    TemplateError,
    build_module_document,
    bundled_templates_root,
    resolve_template_dir,
)
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def make_base(root, base_name="memory"):
    root.mkdir(parents=True, exist_ok=True)
    write_pointer(root, base_name)
    base = root if base_name == "." else root / base_name
    (base / "modules").mkdir(parents=True, exist_ok=True)
    (base / "timeline").mkdir(parents=True, exist_ok=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    return base


# ---------------------------------------------------------------------------
# Choice validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_is_accepted(kind):
    assert TemplateChoice(kind=kind).kind == kind


@pytest.mark.parametrize("nature", NATURES)
def test_every_nature_is_accepted_for_knowledge(nature):
    assert TemplateChoice(kind="knowledge", nature=nature).nature == nature


def test_unknown_kind_is_rejected():
    with pytest.raises(TemplateError, match="Unknown module kind"):
        TemplateChoice(kind="nonsense")


def test_unknown_nature_is_rejected():
    with pytest.raises(TemplateError, match="Unknown nature"):
        TemplateChoice(kind="knowledge", nature="nonsense")


def test_nature_on_implementation_is_rejected():
    """Only knowledge modules carry a Nature."""
    with pytest.raises(TemplateError, match="applies only to"):
        TemplateChoice(kind="implementation", nature="concept")


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_bundled_templates_are_present_for_every_kind(kind):
    """Guards against shipping a kind whose templates were never packaged."""
    assert resolve_template_dir(kind) == bundled_templates_root() / kind


def test_project_templates_win_over_bundled(tmp_path):
    """Local edits must not be silently ignored in favour of the defaults."""
    base = make_base(tmp_path)
    local = base / "templates" / "knowledge"
    local.mkdir(parents=True)
    (local / "module.md").write_text("# [모듈명]\nLOCAL\n", encoding="utf-8")
    (local / "current.md").write_text("# Current\n", encoding="utf-8")

    assert resolve_template_dir("knowledge", base) == local


def test_incomplete_project_templates_fall_back_to_bundled(tmp_path):
    """A half-populated directory should not break module creation."""
    base = make_base(tmp_path)
    local = base / "templates" / "knowledge"
    local.mkdir(parents=True)
    (local / "module.md").write_text("# [모듈명]\n", encoding="utf-8")  # no current.md

    assert resolve_template_dir("knowledge", base) == bundled_templates_root() / "knowledge"


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------


def test_knowledge_document_has_all_sections():
    doc = build_module_document(name="asyncio", kind="knowledge", nature="concept")

    assert doc.startswith("# asyncio")
    assert "# Current Knowledge State: asyncio" in doc
    assert "Decisions" in doc
    assert "# Dependencies" in doc
    assert "# Interface" in doc


def test_implementation_document_uses_path_title():
    doc = build_module_document(name="app/api", kind="implementation")

    assert doc.startswith("# Module: app/api")
    assert "# Current Status: api" in doc


def test_kind_field_is_collapsed_to_the_selection():
    doc = build_module_document(name="m", kind="knowledge", nature="tracker")

    assert "**Kind:** knowledge | **Nature:** tracker" in doc
    # the option list is gone
    assert "concept | reference | analysis" not in doc


def test_other_header_fields_keep_their_option_lists():
    """Only Kind and Nature are resolved; Role and Status stay as authored."""
    doc = build_module_document(name="m", kind="implementation")

    assert "**Role:** leaf | root" in doc
    assert "**Status:** planning | dev | stable | frozen" in doc


def test_implementation_has_no_nature_field():
    doc = build_module_document(name="m", kind="implementation")
    assert "**Nature:**" not in doc


@pytest.mark.parametrize("nature", NATURES)
def test_each_nature_fills_the_body_section(nature):
    doc = build_module_document(name="m", kind="knowledge", nature=nature)

    assert "## 2. 본문" in doc
    # the instruction comment listing the natures must be gone
    assert "성격(Nature)에 맞는 목차를" not in doc
    # a body outline was spliced in
    assert "### 2." in doc


def test_body_heading_appears_exactly_once():
    """The outline repeats the heading it fills; only one may survive."""
    doc = build_module_document(name="m", kind="knowledge", nature="concept")

    assert doc.count("## 2. 본문") == 1


def test_body_heading_has_no_stray_suffix():
    """One authored outline carries a typo'd heading that must not leak."""
    for nature in NATURES:
        doc = build_module_document(name="m", kind="knowledge", nature=nature)
        assert "본문TT" not in doc


def test_blank_line_follows_the_body_heading():
    """Markdown needs a blank line or the first subheading is not parsed."""
    doc = build_module_document(name="m", kind="knowledge", nature="concept")

    assert "## 2. 본문\n\n###" in doc


def test_nature_outlines_differ():
    concept = build_module_document(name="m", kind="knowledge", nature="concept")
    reference = build_module_document(name="m", kind="knowledge", nature="reference")

    assert "핵심 비유" in concept
    assert "핵심 비유" not in reference
    assert "Cheatsheet" in reference


def test_knowledge_without_nature_keeps_the_body_placeholder():
    doc = build_module_document(name="m", kind="knowledge")

    assert "## 2. 본문" in doc
    assert "### 2.1" not in doc


# ---------------------------------------------------------------------------
# Placeholder substitution
# ---------------------------------------------------------------------------


def test_dates_are_substituted():
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    doc = build_module_document(name="m", kind="knowledge", nature="concept")

    assert "YYYY-MM-DD" not in doc
    assert f"**Created:** {today}" in doc


def test_tracker_snapshot_heading_gets_the_date():
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    doc = build_module_document(name="m", kind="knowledge", nature="tracker")

    assert f"### 2.1 현황 스냅샷 ({today} 기준)" in doc


def test_tags_are_inserted_with_a_following_blank_line():
    doc = build_module_document(
        name="m", kind="knowledge", nature="concept", tags=["python", "async"]
    )

    assert "**Tags:** python, async\n\n" in doc


def test_no_tags_leaves_the_field_empty():
    doc = build_module_document(name="m", kind="knowledge", nature="concept")
    assert "**Tags:**" in doc


def test_description_is_inserted_under_the_purpose_heading():
    doc = build_module_document(
        name="m", kind="knowledge", nature="concept", description="비동기 실행 모델"
    )

    purpose = doc.split("## 목적과 목표", 1)[1].split("## ", 1)[0]
    assert "비동기 실행 모델" in purpose


def test_guidance_comments_survive_the_description():
    """The instructional comment stays so it still guides later editing."""
    doc = build_module_document(
        name="m", kind="knowledge", nature="concept", description="설명"
    )

    assert "한 문장. 두 문장이 넘어가면" in doc


def test_nested_module_name_uses_its_basename_for_titles():
    doc = build_module_document(name="AI/basics/vectors", kind="knowledge", nature="concept")

    assert doc.startswith("# vectors")
    assert "# Current Knowledge State: vectors" in doc


# ---------------------------------------------------------------------------
# ModuleManager integration
# ---------------------------------------------------------------------------


def test_create_with_kind_writes_the_template(tmp_path):
    base = make_base(tmp_path)
    manager = ModuleManager(tmp_path)

    path = manager.create("asyncio", description="d", kind="knowledge", nature="concept")

    content = path.read_text(encoding="utf-8")
    assert path == base / "modules" / "asyncio" / "asyncio.md"
    assert "**Kind:** knowledge | **Nature:** concept" in content


def test_create_without_kind_keeps_the_legacy_template(tmp_path):
    """Existing behaviour must be unchanged when no kind is requested."""
    make_base(tmp_path)
    manager = ModuleManager(tmp_path)

    path = manager.create("legacy", description="d")
    content = path.read_text(encoding="utf-8")

    assert content.startswith("# Module: legacy")
    assert "**Kind:**" not in content
    assert "## Overview" in content


def test_bare_nature_implies_knowledge(tmp_path):
    make_base(tmp_path)
    manager = ModuleManager(tmp_path)

    path = manager.create("m", nature="analysis")

    assert "**Kind:** knowledge | **Nature:** analysis" in path.read_text(encoding="utf-8")


def test_default_kind_from_config_is_applied(tmp_path):
    """Lets a knowledge-oriented project opt in once instead of per command."""
    base = make_base(tmp_path)
    (base / "config.yaml").write_text(
        "version: '1.0'\nmodules:\n  default_kind: knowledge\n", encoding="utf-8"
    )
    manager = ModuleManager(tmp_path)

    path = manager.create("m", description="d")

    assert "**Kind:** knowledge" in path.read_text(encoding="utf-8")


def test_explicit_kind_overrides_the_configured_default(tmp_path):
    base = make_base(tmp_path)
    (base / "config.yaml").write_text(
        "version: '1.0'\nmodules:\n  default_kind: knowledge\n", encoding="utf-8"
    )
    manager = ModuleManager(tmp_path)

    path = manager.create("m", kind="implementation")

    assert "**Kind:** implementation" in path.read_text(encoding="utf-8")


def test_create_surfaces_template_errors_as_module_errors(tmp_path):
    make_base(tmp_path)
    manager = ModuleManager(tmp_path)

    with pytest.raises(ModuleError, match="Unknown module kind"):
        manager.create("m", kind="nonsense")


def test_created_module_is_discoverable(tmp_path):
    """A templated module must still be found by the usual discovery paths."""
    make_base(tmp_path)
    manager = ModuleManager(tmp_path)
    manager.create("AI/basics", kind="knowledge", nature="concept")

    names = [str(p).replace("\\", "/") for p in manager.discover_all_modules()]

    assert "AI/basics" in names
    assert manager.resolve_module_doc("AI/basics") is not None
