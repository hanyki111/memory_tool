"""Tests for repairing wiki links after a module is moved by hand.

Moving a module in Obsidian is the natural way to reorganize, and discovery
already copes -- it scans the filesystem. What breaks is every ``[[old/path]]``
aimed at the old location, silently, because a broken wiki link renders as
ordinary text rather than an error. These cover the detection, the "report
rather than guess" boundary, and the rewrite itself.
"""

import pytest

from memory_tool.core.connections import ConnectionParser
from memory_tool.core.module import ModuleManager
from memory_tool.core.relink import (
    apply_plan,
    build_plan,
    format_plan,
    link_pattern_for,
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
def base(tmp_path, monkeypatch):
    """A knowledge base rooted at tmp_path, with modules/ ready."""
    root = tmp_path / "proj"
    root.mkdir(parents=True, exist_ok=True)
    write_pointer(root, "memory")
    b = root / "memory"
    (b / "modules").mkdir(parents=True, exist_ok=True)
    (b / "timeline").mkdir(parents=True, exist_ok=True)
    (b / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")

    clear_cache()
    return b


def write_module(base, name: str, body: str = "") -> None:
    """Create a [Folder]/[Folder].md module."""
    basename = name.split("/")[-1]
    directory = base / "modules" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{basename}.md").write_text(
        f"# Module: {name}\n\n{body}\n", encoding="utf-8"
    )


def manager_for(base) -> ModuleManager:
    # ModuleManager takes the *project root* and derives the base folder from the
    # pointer written by the fixture; `base` is root/"memory".
    return ModuleManager(base.parent)


# ---------------------------------------------------------------------------
# The link pattern -- non-ASCII names were previously invisible
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("[[a/b]]", ["a/b"]),
        ("[[게임 분석/니케]]", ["게임 분석/니케"]),          # was unmatched
        ("[[master|마스터]]", ["master"]),                  # alias stripped
        ("[[a/b#section]]", ["a/b"]),                       # section stripped
        ("[[a^block|alias]]", ["a"]),
        ("[[ spaced ]]", ["spaced"]),
        ("no link here", []),
        ("[[]]", []),
    ],
)
def test_link_pattern(text, expected):
    assert ConnectionParser.LINK_PATTERN.findall(text) == expected


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_no_broken_links_is_an_empty_plan(base):
    write_module(base, "a")
    write_module(base, "b", "See [[a]].")

    assert build_plan(manager_for(base)).is_empty


def test_moved_module_is_detected_by_suffix(base):
    # "core" used to live at the top level and now sits under "tools".
    write_module(base, "tools/core")
    write_module(base, "docs", "See [[core]].")

    plan = build_plan(manager_for(base))

    assert len(plan.proposals) == 1
    assert plan.proposals[0].old == "core"
    assert plan.proposals[0].new == "tools/core"
    assert plan.unresolved == []


def test_reparented_module_is_detected_by_basename(base):
    write_module(base, "new-parent/child")
    write_module(base, "docs", "See [[old-parent/child]].")

    plan = build_plan(manager_for(base))

    assert len(plan.proposals) == 1
    assert plan.proposals[0].new == "new-parent/child"


def test_ambiguous_move_is_reported_not_guessed(base):
    # Two modules could be the new home; picking one would silently repoint the
    # link at the wrong document, which is worse than leaving it broken.
    write_module(base, "x/shared")
    write_module(base, "y/shared")
    write_module(base, "docs", "See [[old/shared]].")

    plan = build_plan(manager_for(base))

    assert plan.proposals == []
    assert len(plan.unresolved) == 1
    assert plan.unresolved[0].candidates == ["x/shared", "y/shared"]


def test_unknown_target_is_reported(base):
    # Documentation that mentions [[module-name]] as an example, for instance.
    write_module(base, "docs", "Write [[module-name]] to link.")

    plan = build_plan(manager_for(base))

    assert plan.proposals == []
    assert plan.unresolved[0].reason == "no module with that name exists"


def test_exact_match_wins_over_basename(base):
    # "a/target" exists, so a link to it is not broken even though "b/target"
    # would also match on basename.
    write_module(base, "a/target")
    write_module(base, "b/target")
    write_module(base, "docs", "See [[a/target]].")

    assert build_plan(manager_for(base)).is_empty


def test_korean_module_move_is_detected(base):
    write_module(base, "게임 분석/니케")
    write_module(base, "docs", "See [[니케]].")

    plan = build_plan(manager_for(base))

    assert len(plan.proposals) == 1
    assert plan.proposals[0].new == "게임 분석/니케"


# ---------------------------------------------------------------------------
# Rewriting
# ---------------------------------------------------------------------------


def docs_text(base) -> str:
    return (base / "modules" / "docs" / "docs.md").read_text(encoding="utf-8")


def test_apply_rewrites_the_link(base):
    write_module(base, "tools/core")
    write_module(base, "docs", "See [[core]] for details.")

    plan = build_plan(manager_for(base))
    changed = apply_plan(plan)

    assert changed == 1
    assert "[[tools/core]]" in docs_text(base)
    assert "[[core]]" not in docs_text(base)


def test_dry_run_writes_nothing(base):
    write_module(base, "tools/core")
    write_module(base, "docs", "See [[core]].")
    before = docs_text(base)

    plan = build_plan(manager_for(base))
    changed = apply_plan(plan, dry_run=True)

    assert changed == 1          # still reports what it would touch
    assert docs_text(base) == before


def test_alias_survives_the_rewrite(base):
    # Losing the alias would quietly change what the sentence reads like.
    write_module(base, "tools/core")
    write_module(base, "docs", "See [[core|the core module]].")

    apply_plan(build_plan(manager_for(base)))

    assert "[[tools/core|the core module]]" in docs_text(base)


def test_section_reference_survives_the_rewrite(base):
    write_module(base, "tools/core")
    write_module(base, "docs", "See [[core#Design]].")

    apply_plan(build_plan(manager_for(base)))

    assert "[[tools/core#Design]]" in docs_text(base)


def test_every_occurrence_in_a_file_is_rewritten(base):
    write_module(base, "tools/core")
    write_module(base, "docs", "[[core]] and again [[core]] and [[core|x]].")

    apply_plan(build_plan(manager_for(base)))

    text = docs_text(base)
    assert text.count("[[tools/core") == 3


def test_multiple_moves_in_one_file(base):
    write_module(base, "tools/core")
    write_module(base, "tools/search")
    write_module(base, "docs", "[[core]] and [[search]].")

    changed = apply_plan(build_plan(manager_for(base)))

    assert changed == 1  # one file, read and written once
    text = docs_text(base)
    assert "[[tools/core]]" in text and "[[tools/search]]" in text


def test_unresolved_links_are_left_untouched(base):
    write_module(base, "x/shared")
    write_module(base, "y/shared")
    write_module(base, "docs", "See [[old/shared]].")

    apply_plan(build_plan(manager_for(base)))

    assert "[[old/shared]]" in docs_text(base)


def test_unrelated_text_is_not_touched(base):
    write_module(base, "tools/core")
    write_module(base, "docs", "The word core appears bare, and [[core]] linked.")

    apply_plan(build_plan(manager_for(base)))

    text = docs_text(base)
    assert "The word core appears bare" in text
    assert "[[tools/core]]" in text


# ---------------------------------------------------------------------------
# Pattern construction
# ---------------------------------------------------------------------------


def test_link_pattern_for_matches_both_separators(base):
    pattern = link_pattern_for("a/b")

    assert pattern.search("[[a/b]]")
    assert pattern.search(r"[[a\b]]")
    assert pattern.search("[[ a/b ]]")


def test_link_pattern_for_does_not_match_a_longer_path(base):
    pattern = link_pattern_for("a/b")

    assert not pattern.search("[[a/b/c]]")
    assert not pattern.search("[[x/a/b]]")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def test_format_plan_says_nothing_to_do(base):
    assert "No broken module links" in format_plan(build_plan(manager_for(base)))


def test_format_plan_lists_both_sections(base):
    write_module(base, "tools/core")
    write_module(base, "x/shared")
    write_module(base, "y/shared")
    write_module(base, "docs", "[[core]] and [[old/shared]].")

    report = format_plan(build_plan(manager_for(base)), dry_run=True)

    assert "Would repair" in report
    assert "[[core]] -> [[tools/core]]" in report
    assert "Needs a decision" in report
    assert "ambiguous" in report
