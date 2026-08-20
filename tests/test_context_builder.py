"""Tests for context building (memory_tool.context.builder).

Two long-standing bugs made `mcontext` produce a near-empty context file:
  - timeline lookup omitted the `daily/` segment that records are written to
  - module discovery only matched the legacy `current.md` filename
"""

import pytest

from memory_tool.context.builder import ContextBuilder
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def make_base(root, base_name=".memory"):
    root.mkdir(parents=True, exist_ok=True)
    write_pointer(root, base_name)
    base = root if base_name == "." else root / base_name
    (base / "timeline").mkdir(parents=True, exist_ok=True)
    (base / "modules").mkdir(parents=True, exist_ok=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    return base


def write_timeline(base, date, daily=True, layout="day"):
    """Create a timeline file in either the daily/ or the legacy location.

    ``layout`` picks the filename: "day" for 20.md, "date" for 2026-08-20.md.
    Both exist in the wild, and the context file has to label either correctly.
    """
    parent = base / "timeline"
    if daily:
        parent = parent / "daily"
    parent = parent / date.strftime("%Y-%m")
    parent.mkdir(parents=True, exist_ok=True)
    stem = date.strftime("%Y-%m-%d") if layout == "date" else date.strftime("%d")
    path = parent / f"{stem}.md"
    path.write_text(f"# {date} Timeline\n- 10:00 | entry\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Timeline discovery
# ---------------------------------------------------------------------------


def test_finds_timeline_in_daily_structure(tmp_path):
    """The location `m` actually writes to."""
    from datetime import date

    base = make_base(tmp_path)
    expected = write_timeline(base, date.today(), daily=True)

    paths = ContextBuilder(tmp_path).get_recent_timeline_paths(days=3)

    assert paths == [expected]


def test_finds_timeline_in_legacy_structure(tmp_path):
    from datetime import date

    base = make_base(tmp_path)
    expected = write_timeline(base, date.today(), daily=False)

    paths = ContextBuilder(tmp_path).get_recent_timeline_paths(days=3)

    assert paths == [expected]


def test_daily_wins_when_both_locations_exist(tmp_path):
    """Avoid reporting the same day twice during a partial migration."""
    from datetime import date

    base = make_base(tmp_path)
    write_timeline(base, date.today(), daily=False)
    daily = write_timeline(base, date.today(), daily=True)

    paths = ContextBuilder(tmp_path).get_recent_timeline_paths(days=3)

    assert paths == [daily]


def test_collects_multiple_recent_days(tmp_path):
    from datetime import date, timedelta

    base = make_base(tmp_path)
    today = date.today()
    for offset in range(3):
        write_timeline(base, today - timedelta(days=offset), daily=True)

    paths = ContextBuilder(tmp_path).get_recent_timeline_paths(days=3)

    assert len(paths) == 3


def test_days_window_is_respected(tmp_path):
    from datetime import date, timedelta

    base = make_base(tmp_path)
    today = date.today()
    write_timeline(base, today, daily=True)
    write_timeline(base, today - timedelta(days=5), daily=True)

    paths = ContextBuilder(tmp_path).get_recent_timeline_paths(days=3)

    assert len(paths) == 1


def test_no_timeline_returns_empty(tmp_path):
    make_base(tmp_path)
    assert ContextBuilder(tmp_path).get_recent_timeline_paths(days=3) == []


# ---------------------------------------------------------------------------
# The date each timeline file is labelled with
# ---------------------------------------------------------------------------


def timeline_section(tmp_path):
    """The "Recent Timeline" lines of a freshly built context file."""
    content = ContextBuilder(tmp_path).build_context_content()
    body = content.split("## Recent Timeline", 1)[1]
    return [line for line in body.split("\n") if line.startswith("- **")]


def test_dated_filenames_are_labelled_with_their_date(tmp_path):
    """The regression: the month folder was prepended to a full-date filename.

    "2026-08" + "-" + "2026-08-20" produced "2026-08-2026-08-20", which is not
    a date in any format and is the first thing an AI session reads.
    """
    from datetime import date

    base = make_base(tmp_path)
    today = date.today()
    write_timeline(base, today, daily=True, layout="date")

    lines = timeline_section(tmp_path)

    assert len(lines) == 1
    assert lines[0].startswith(f"- **{today.isoformat()}**:")


def test_day_filenames_are_labelled_with_the_full_date(tmp_path):
    """20.md means nothing without its folder, so the label supplies it."""
    from datetime import date

    base = make_base(tmp_path)
    today = date.today()
    write_timeline(base, today, daily=True, layout="day")

    lines = timeline_section(tmp_path)

    assert len(lines) == 1
    assert lines[0].startswith(f"- **{today.isoformat()}**:")


def test_legacy_location_is_labelled_the_same_way(tmp_path):
    from datetime import date

    base = make_base(tmp_path)
    today = date.today()
    write_timeline(base, today, daily=False, layout="date")

    lines = timeline_section(tmp_path)

    assert len(lines) == 1
    assert lines[0].startswith(f"- **{today.isoformat()}**:")


# ---------------------------------------------------------------------------
# Module discovery
# ---------------------------------------------------------------------------


def test_finds_encapsulated_single_file_modules(tmp_path):
    """<folder>/<folder>.md -- the current layout, previously invisible."""
    base = make_base(tmp_path)
    mod = base / "modules" / "core-system"
    mod.mkdir(parents=True)
    doc = mod / "core-system.md"
    doc.write_text("# core-system\n", encoding="utf-8")

    docs = ContextBuilder(tmp_path).get_module_docs()

    assert docs == {"core-system": doc}


def test_finds_nested_encapsulated_modules(tmp_path):
    base = make_base(tmp_path)
    mod = base / "modules" / "memory-tool" / "core-system"
    mod.mkdir(parents=True)
    doc = mod / "core-system.md"
    doc.write_text("# core-system\n", encoding="utf-8")

    docs = ContextBuilder(tmp_path).get_module_docs()

    assert "memory-tool/core-system" in docs
    assert docs["memory-tool/core-system"] == doc


def test_finds_legacy_multi_file_modules(tmp_path):
    base = make_base(tmp_path)
    mod = base / "modules" / "legacy-mod"
    mod.mkdir(parents=True)
    doc = mod / "current.md"
    doc.write_text("# legacy\n", encoding="utf-8")

    docs = ContextBuilder(tmp_path).get_module_docs()

    assert docs == {"legacy-mod": doc}


def test_finds_flat_single_file_modules(tmp_path):
    """modules/A/B.md -- the .md as a sibling of its subfolder."""
    base = make_base(tmp_path)
    parent = base / "modules" / "AI"
    parent.mkdir(parents=True)
    doc = parent / "basics.md"
    doc.write_text("# basics\n", encoding="utf-8")

    docs = ContextBuilder(tmp_path).get_module_docs()

    assert "AI/basics" in docs
    assert docs["AI/basics"] == doc


def test_finds_all_layouts_together(tmp_path):
    """A real knowledge base mixes layouts; all must be reported."""
    base = make_base(tmp_path)
    modules = base / "modules"

    (modules / "encapsulated").mkdir(parents=True)
    (modules / "encapsulated" / "encapsulated.md").write_text("x", encoding="utf-8")
    (modules / "legacy").mkdir(parents=True)
    (modules / "legacy" / "current.md").write_text("x", encoding="utf-8")
    (modules / "group").mkdir(parents=True)
    (modules / "group" / "flat.md").write_text("x", encoding="utf-8")

    docs = ContextBuilder(tmp_path).get_module_docs()

    assert set(docs) == {"encapsulated", "legacy", "group/flat"}


def test_module_statuses_matches_module_docs(tmp_path):
    """The old name stays available for existing callers."""
    base = make_base(tmp_path)
    mod = base / "modules" / "m1"
    mod.mkdir(parents=True)
    (mod / "m1.md").write_text("x", encoding="utf-8")

    builder = ContextBuilder(tmp_path)
    assert builder.get_module_statuses() == builder.get_module_docs()


def test_no_modules_returns_empty(tmp_path):
    make_base(tmp_path)
    assert ContextBuilder(tmp_path).get_module_docs() == {}


# ---------------------------------------------------------------------------
# Path rendering in the generated file
# ---------------------------------------------------------------------------


def test_context_paths_are_forward_slashed_and_relative(tmp_path):
    from datetime import date

    base = make_base(tmp_path)
    write_timeline(base, date.today(), daily=True)
    mod = base / "modules" / "m1"
    mod.mkdir(parents=True)
    (mod / "m1.md").write_text("x", encoding="utf-8")

    content = ContextBuilder(tmp_path).build_context_content()

    assert ".memory/timeline/daily/" in content
    assert ".memory/modules/m1/m1.md" in content
    assert "\\" not in content.split("## Module Status")[0].split("## Recent Timeline")[-1]


def test_context_paths_have_no_prefix_for_root_base(tmp_path):
    """With base ".", content sits at the project root and needs no prefix."""
    from datetime import date

    base = make_base(tmp_path, base_name=".")
    write_timeline(base, date.today(), daily=True)

    content = ContextBuilder(tmp_path).build_context_content()

    assert "timeline/daily/" in content
    assert "./timeline" not in content


def test_context_reports_timeline_and_modules_together(tmp_path):
    from datetime import date

    base = make_base(tmp_path)
    write_timeline(base, date.today(), daily=True)
    for name in ("a", "b"):
        d = base / "modules" / name
        d.mkdir(parents=True)
        (d / f"{name}.md").write_text("x", encoding="utf-8")

    builder = ContextBuilder(tmp_path)

    assert len(builder.get_recent_timeline_paths(days=3)) == 1
    assert len(builder.get_module_docs()) == 2
