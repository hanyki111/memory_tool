"""Tests for timeline sorting (memory_tool.core.sort).

Sorting used to treat any "- " line as an entry, gather them all, and append the
untimed ones at the end. That mangled any timeline file holding a note's own list
items -- for example an Obsidian Daily Note template, which is exactly what
happens when the Calendar plugin creates the file before `m` writes to it.
"""

import pytest

from memory_tool.core.sort import TimelineSorter
from memory_tool.core.timeline import Timeline
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def make_timeline_file(tmp_path, content, name="14.md"):
    write_pointer(tmp_path, ".")
    directory = tmp_path / "timeline" / "daily" / "2026-08"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(content, encoding="utf-8")
    clear_cache()
    return path


def sort_and_read(tmp_path, path):
    sorter = TimelineSorter(tmp_path)
    total, sorted_count = sorter.sort_file(path, create_backup=False)
    return path.read_text(encoding="utf-8").splitlines(), total, sorted_count


# ---------------------------------------------------------------------------
# Ordinary timeline files
# ---------------------------------------------------------------------------


def test_entries_are_sorted_by_time(tmp_path):
    path = make_timeline_file(
        tmp_path,
        "# 2026-08-14 Timeline\n- 14:30 | third\n- 09:00 | first\n- 11:15 | second\n",
    )

    lines, total, sorted_count = sort_and_read(tmp_path, path)

    assert lines == [
        "# 2026-08-14 Timeline",
        "- 09:00 | first",
        "- 11:15 | second",
        "- 14:30 | third",
    ]
    assert (total, sorted_count) == (3, 3)


def test_header_is_preserved(tmp_path):
    path = make_timeline_file(
        tmp_path, "# 2026-08-14 Timeline\n- 10:00 | a\n- 09:00 | b\n"
    )

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines[0] == "# 2026-08-14 Timeline"


def test_equal_times_keep_their_recorded_order(tmp_path):
    path = make_timeline_file(
        tmp_path,
        "# 2026-08-14 Timeline\n- 09:00 | first recorded\n- 09:00 | second recorded\n",
    )

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines[1] == "- 09:00 | first recorded"
    assert lines[2] == "- 09:00 | second recorded"


def test_already_sorted_file_is_unchanged(tmp_path):
    content = "# 2026-08-14 Timeline\n- 09:00 | a\n- 10:00 | b\n"
    path = make_timeline_file(tmp_path, content)

    lines, _, _ = sort_and_read(tmp_path, path)

    assert "\n".join(lines) + "\n" == content


def test_empty_file_is_handled(tmp_path):
    path = make_timeline_file(tmp_path, "")

    sorter = TimelineSorter(tmp_path)
    assert sorter.sort_file(path, create_backup=False) == (0, 0)


# ---------------------------------------------------------------------------
# Files that also hold note content (the Obsidian Calendar case)
# ---------------------------------------------------------------------------


TEMPLATED = """## Tasks
- [ ] buy groceries

## Notes

- 09:00 | later entry
- 08:00 | earlier entry
"""


def test_template_structure_survives_sorting(tmp_path):
    """Headings, blank lines and checkboxes must stay exactly where they are."""
    path = make_timeline_file(tmp_path, TEMPLATED)

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines == [
        "## Tasks",
        "- [ ] buy groceries",
        "",
        "## Notes",
        "",
        "- 08:00 | earlier entry",
        "- 09:00 | later entry",
    ]


def test_checkbox_is_not_moved_to_the_end(tmp_path):
    path = make_timeline_file(tmp_path, TEMPLATED)

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines[1] == "- [ ] buy groceries"
    assert lines[-1].startswith("- 09:00")


def test_untimed_top_level_line_stays_in_place(tmp_path):
    path = make_timeline_file(
        tmp_path,
        "# 2026-08-14 Timeline\n- 10:00 | a\n- a plain note\n- 09:00 | b\n",
    )

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines[2] == "- a plain note"


def test_trailing_heading_is_not_relocated(tmp_path):
    path = make_timeline_file(
        tmp_path,
        "# 2026-08-14 Timeline\n- 10:00 | a\n- 09:00 | b\n\n## Footer\ntext\n",
    )

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines[-2:] == ["## Footer", "text"]


# ---------------------------------------------------------------------------
# Continuation lines
# ---------------------------------------------------------------------------


def test_sub_bullets_travel_with_their_entry(tmp_path):
    """Hand-edited detail lines must not be stranded when the order changes."""
    path = make_timeline_file(
        tmp_path,
        "# 2026-08-14 Timeline\n"
        "- 14:00 | later\n"
        "  - detail A\n"
        "  - detail B\n"
        "- 09:00 | earlier\n"
        "  - detail C\n",
    )

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines == [
        "# 2026-08-14 Timeline",
        "- 09:00 | earlier",
        "  - detail C",
        "- 14:00 | later",
        "  - detail A",
        "  - detail B",
    ]


def test_indented_continuation_text_travels_too(tmp_path):
    path = make_timeline_file(
        tmp_path,
        "# 2026-08-14 Timeline\n- 14:00 | later\n    continued text\n- 09:00 | earlier\n",
    )

    lines, _, _ = sort_and_read(tmp_path, path)

    assert lines[1] == "- 09:00 | earlier"
    assert lines[2] == "- 14:00 | later"
    assert lines[3] == "    continued text"


def test_sub_bullets_do_not_count_as_sorted_entries(tmp_path):
    path = make_timeline_file(
        tmp_path, "# 2026-08-14 Timeline\n- 10:00 | a\n  - detail\n"
    )

    _, total, sorted_count = sort_and_read(tmp_path, path)

    assert sorted_count == 1


# ---------------------------------------------------------------------------
# Path resolution shared with msort
# ---------------------------------------------------------------------------


def test_resolve_existing_file_finds_daily_layout(tmp_path):
    from datetime import date

    path = make_timeline_file(tmp_path, "# x\n")
    found = Timeline.resolve_existing_file(tmp_path / "timeline", date(2026, 8, 14))

    assert found == path


def test_resolve_existing_file_finds_legacy_layout(tmp_path):
    from datetime import date

    write_pointer(tmp_path, ".")
    legacy = tmp_path / "timeline" / "2026-08"
    legacy.mkdir(parents=True)
    path = legacy / "14.md"
    path.write_text("# x\n", encoding="utf-8")

    found = Timeline.resolve_existing_file(tmp_path / "timeline", date(2026, 8, 14))

    assert found == path


def test_resolve_existing_file_prefers_daily(tmp_path):
    from datetime import date

    daily = make_timeline_file(tmp_path, "# daily\n")
    legacy = tmp_path / "timeline" / "2026-08"
    legacy.mkdir(parents=True)
    (legacy / "14.md").write_text("# legacy\n", encoding="utf-8")

    found = Timeline.resolve_existing_file(tmp_path / "timeline", date(2026, 8, 14))

    assert found == daily


def test_resolve_existing_file_returns_none_when_absent(tmp_path):
    from datetime import date

    write_pointer(tmp_path, ".")
    (tmp_path / "timeline").mkdir()

    assert Timeline.resolve_existing_file(tmp_path / "timeline", date(2026, 8, 14)) is None
