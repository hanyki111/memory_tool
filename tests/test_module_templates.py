"""Tests for MOP v3.2 module templates (memory_tool.core.module_templates).

Templates are authored as separate documents but modules are stored as a single
file, so the assembly step and its placeholder substitution are what these cover.
"""

import pytest

from memory_tool.core.module import ModuleError, ModuleManager
from memory_tool.core.module_templates import (
    KIND_NATURES,
    KINDS,
    NATURES,
    TemplateChoice,
    kind_for_nature,
    TemplateError,
    build_module_document,
    bundled_templates_root,
    load_template_parts,
    merge_template_dir,
    parse_single_file_template,
    resolve_template_dir,
    single_file_name,
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


#: Every (kind, nature) pair the templates offer, for parametrized tests.
NATURE_PAIRS = [
    (kind, nature)
    for kind, natures in KIND_NATURES.items()
    for nature in natures
]


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_is_accepted(kind):
    assert TemplateChoice(kind=kind).kind == kind


@pytest.mark.parametrize("kind,nature", NATURE_PAIRS)
def test_every_nature_is_accepted_by_its_kind(kind, nature):
    assert TemplateChoice(kind=kind, nature=nature).nature == nature


def test_nature_names_are_unique_across_kinds():
    """A bare --nature infers its kind, which only works if names don't repeat."""
    assert len(NATURES) == len(set(NATURES))


@pytest.mark.parametrize("kind,nature", NATURE_PAIRS)
def test_kind_for_nature_round_trips(kind, nature):
    assert kind_for_nature(nature) == kind


def test_kind_for_an_unknown_nature_is_none():
    assert kind_for_nature("nonsense") is None


def test_unknown_kind_is_rejected():
    with pytest.raises(TemplateError, match="Unknown module kind"):
        TemplateChoice(kind="nonsense")


def test_unknown_nature_is_rejected():
    with pytest.raises(TemplateError, match="Unknown nature"):
        TemplateChoice(kind="knowledge", nature="nonsense")


def test_nature_belonging_to_another_kind_is_rejected():
    """'plan' is an intent outline; asking for it on knowledge is a mistake."""
    with pytest.raises(TemplateError, match="belongs to 'intent'"):
        TemplateChoice(kind="knowledge", nature="plan")


def test_nature_on_implementation_is_rejected():
    """Only knowledge and intent modules carry a Nature."""
    with pytest.raises(TemplateError, match="applies only to"):
        TemplateChoice(kind="implementation", nature="concept")


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_bundled_templates_are_present_for_every_kind(kind):
    """Guards against shipping a kind whose templates were never packaged."""
    _, origin = load_template_parts(kind)
    assert origin == bundled_templates_root() / single_file_name(kind)


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

    _, origin = load_template_parts("knowledge", base)
    assert origin == bundled_templates_root() / single_file_name("knowledge")


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


@pytest.mark.parametrize("kind,nature", NATURE_PAIRS)
def test_each_nature_fills_the_body_section(kind, nature):
    doc = build_module_document(name="m", kind=kind, nature=nature)

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
    for kind, nature in NATURE_PAIRS:
        doc = build_module_document(name="m", kind=kind, nature=nature)
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


@pytest.mark.parametrize("kind", KINDS)
def test_wiki_link_examples_survive_substitution(kind):
    """[[모듈명]] is a link example, not a field to fill.

    The placeholders and wiki links share the bracket, so a plain replace
    rewrote [[모듈명]] to [name] -- neither a link nor a visible placeholder.
    """
    doc = build_module_document(name="asyncio", kind=kind)

    assert "[[모듈명]]" in doc
    assert "[asyncio]" not in doc


def test_intent_outlines_differ():
    idea = build_module_document(name="m", kind="intent", nature="idea")
    plan = build_module_document(name="m", kind="intent", nature="plan")

    assert "씨앗" in idea
    assert "씨앗" not in plan
    assert "Definition of Done" in plan


def test_intent_header_carries_stage_and_decision_state():
    """Intent fails by drifting, so its header must show where it stands."""
    doc = build_module_document(name="m", kind="intent", nature="inquiry")

    assert "**Stage:**" in doc
    assert "**결정 상태:**" in doc


def test_intent_review_date_is_not_filled_in():
    """The review date is a future date the author picks, not the created date.

    It is authored as ____-__-__ precisely so the YYYY-MM-DD substitution leaves
    it alone -- a review date silently set to today would read as already due.
    """
    doc = build_module_document(name="m", kind="intent", nature="plan")

    assert "**다음 판정일:** ____-__-__" in doc


def test_intent_document_has_an_exit_section():
    """An intent module has to name how it stops being one."""
    doc = build_module_document(name="m", kind="intent", nature="idea")

    assert "## 7. 종결 처리 (Exit)" in doc


def test_intent_interface_exposes_only_settled_conclusions():
    doc = build_module_document(name="m", kind="intent", nature="inquiry")

    assert "## 확정 결론 (인용 가능)" in doc


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


def test_bare_nature_implies_intent_when_the_name_is_an_intent_one(tmp_path):
    """Nature names name their own kind, so --nature plan needs no --kind."""
    make_base(tmp_path)
    manager = ModuleManager(tmp_path)

    path = manager.create("PLAN-release", nature="plan")

    assert "**Kind:** intent | **Nature:** plan" in path.read_text(encoding="utf-8")


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


# ---------------------------------------------------------------------------
# Single-file templates
# ---------------------------------------------------------------------------


SINGLE = """<!-- header comment, ignored -->

<!-- part: module -->

# [모듈명]

**Kind:** knowledge | **Nature:** concept | reference | analysis | tracker | method
**Tags:** 

---

<!-- part: current -->

# Current Knowledge State: [주제]

## 2. 본문

<!-- placeholder -->

## 3. Open Questions

---

<!-- part: natures -->

## concept (개념)

```markdown
## 2. 본문

### 2.1 왜 필요한가
```

## reference (레퍼런스)

```markdown
## 2. 본문

### 2.0 요약 조회표
```
"""


def test_parse_single_file_splits_on_markers():
    parts = parse_single_file_template(SINGLE)

    assert list(parts) == ["module", "current", "natures"]
    assert parts["module"].startswith("# [모듈명]")
    assert parts["current"].startswith("# Current Knowledge State")


def test_parse_drops_the_separator_before_the_next_marker():
    # The "---" between sections belongs to the layout, not to the section that
    # happens to precede it; keeping it would double the rule on assembly.
    parts = parse_single_file_template(SINGLE)
    assert not parts["module"].rstrip().endswith("---")
    assert not parts["current"].rstrip().endswith("---")


def test_text_before_the_first_marker_is_ignored():
    parts = parse_single_file_template(SINGLE)
    assert "header comment" not in "".join(parts.values())


def test_single_file_project_template_wins_over_bundled(tmp_path):
    base = make_base(tmp_path)
    templates = base / "templates"
    templates.mkdir(parents=True)
    (templates / single_file_name("knowledge")).write_text(SINGLE, encoding="utf-8")

    parts, origin = load_template_parts("knowledge", base)

    assert origin == templates / "knowledge.md"
    assert "[모듈명]" in parts["module"]


def test_single_file_wins_over_a_directory_at_the_same_level(tmp_path):
    # Both forms present: the merged file is the current one, so it takes
    # precedence rather than the leftover directory it was merged from.
    base = make_base(tmp_path)
    templates = base / "templates"
    directory = templates / "knowledge"
    directory.mkdir(parents=True)
    (directory / "module.md").write_text("# OLD\n", encoding="utf-8")
    (directory / "current.md").write_text("# OLD current\n", encoding="utf-8")
    (templates / single_file_name("knowledge")).write_text(SINGLE, encoding="utf-8")

    _, origin = load_template_parts("knowledge", base)

    assert origin == templates / "knowledge.md"


def test_single_file_missing_a_required_part_is_an_error(tmp_path):
    base = make_base(tmp_path)
    templates = base / "templates"
    templates.mkdir(parents=True)
    (templates / single_file_name("knowledge")).write_text(
        "<!-- part: module -->\n\n# [모듈명]\n", encoding="utf-8"
    )

    with pytest.raises(TemplateError) as exc:
        load_template_parts("knowledge", base)

    assert "current" in str(exc.value)


def test_build_from_a_single_file_template(tmp_path):
    base = make_base(tmp_path)
    templates = base / "templates"
    templates.mkdir(parents=True)
    (templates / single_file_name("knowledge")).write_text(SINGLE, encoding="utf-8")

    doc = build_module_document(
        name="a/asyncio", kind="knowledge", nature="reference", memory_path=base
    )

    assert doc.startswith("# asyncio")
    assert "### 2.0 요약 조회표" in doc      # chosen nature spliced in
    assert "### 2.1 왜 필요한가" not in doc  # the others never appear
    assert "part: natures" not in doc        # the menu is not emitted


def test_unknown_nature_in_a_single_file_names_the_file(tmp_path):
    base = make_base(tmp_path)
    templates = base / "templates"
    templates.mkdir(parents=True)
    (templates / single_file_name("knowledge")).write_text(SINGLE, encoding="utf-8")

    with pytest.raises(TemplateError) as exc:
        build_module_document(
            name="x", kind="knowledge", nature="tracker", memory_path=base
        )

    assert "knowledge.md" in str(exc.value)


# ---------------------------------------------------------------------------
# Merging a directory set into one file
# ---------------------------------------------------------------------------


def test_merge_produces_a_parsable_single_file(tmp_path):
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "module.md").write_text("# [모듈명]\n", encoding="utf-8")
    (directory / "current.md").write_text("# Current\n", encoding="utf-8")
    (directory / "natures.md").write_text("## concept\n\n```markdown\nX\n```\n", encoding="utf-8")

    parts = parse_single_file_template(merge_template_dir(directory))

    assert list(parts) == ["module", "current", "natures"]


def test_merge_refuses_an_incomplete_set(tmp_path):
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "module.md").write_text("# [모듈명]\n", encoding="utf-8")

    with pytest.raises(TemplateError) as exc:
        merge_template_dir(directory)

    assert "current.md" in str(exc.value)


def test_merged_template_builds_the_same_document(tmp_path):
    """The merge must be a pure re-packaging, not a rewrite."""
    base = make_base(tmp_path)
    directory = base / "templates" / "knowledge"
    directory.mkdir(parents=True)
    (directory / "module.md").write_text(
        "# [모듈명]\n\n**Kind:** knowledge | **Role:** leaf\n", encoding="utf-8"
    )
    (directory / "current.md").write_text(
        "# Current Knowledge State: [주제]\n\n## 2. 본문\n\n<!-- ph -->\n\n## 3. Next\n",
        encoding="utf-8",
    )
    (directory / "natures.md").write_text(
        "## concept\n\n```markdown\n## 2. 본문\n\n### 2.1 A\n```\n", encoding="utf-8"
    )

    from_dir = build_module_document("a/b", "knowledge", "concept", memory_path=base)

    merged = merge_template_dir(directory)
    (base / "templates" / single_file_name("knowledge")).write_text(merged, encoding="utf-8")

    from_single = build_module_document("a/b", "knowledge", "concept", memory_path=base)

    assert from_dir == from_single
