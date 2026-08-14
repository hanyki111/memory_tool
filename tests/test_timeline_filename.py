"""Tests for the configurable timeline filename layout.

Obsidian's Calendar and Periodic Notes plugins identify a daily note by parsing
its *basename* against the last "/" segment of the date format. With "21.md"
naming that segment is "DD", so every month's 21.md resolves to the same date
and clicking a day opens whichever month the vault happened to list first.
Naming files "2026-08-21.md" makes each basename unique.
"""

from datetime import date

import pytest

from memory_tool.core.timeline import (
    DEFAULT_FILENAME_LAYOUT,
    FILENAME_LAYOUTS,
    Timeline,
    TimelineError,
    apply_filename_migration,
    date_from_timeline_path,
    plan_filename_migration,
    timeline_filename,
)
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def make_base(root, layout=None):
    root.mkdir(parents=True, exist_ok=True)
    write_pointer(root, ".")
    (root / "timeline" / "daily").mkdir(parents=True, exist_ok=True)
    config = "version: '1.0'\n"
    if layout:
        config += f"timeline:\n  filename: {layout}\n"
    (root / "config.yaml").write_text(config, encoding="utf-8")
    clear_cache()
    return root


def write_file(root, year_month, name, body="- 10:00 | entry\n"):
    directory = root / "timeline" / "daily" / year_month
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(f"# {year_month} Timeline\n{body}", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Filename construction
# ---------------------------------------------------------------------------


def test_day_layout_uses_the_day_only():
    assert timeline_filename(date(2026, 8, 21), "day") == "21.md"


def test_date_layout_uses_the_full_date():
    assert timeline_filename(date(2026, 8, 21), "date") == "2026-08-21.md"


def test_default_layout_is_day():
    assert DEFAULT_FILENAME_LAYOUT == "day"
    assert timeline_filename(date(2026, 8, 21)) == "21.md"


def test_date_basenames_are_unique_across_months():
    """The property Obsidian's lookup depends on."""
    names = {
        timeline_filename(date(2026, month, 21), "date") for month in (1, 2, 3, 8)
    }
    assert len(names) == 4

    colliding = {timeline_filename(date(2026, m, 21), "day") for m in (1, 2, 3, 8)}
    assert colliding == {"21.md"}


# ---------------------------------------------------------------------------
# Parsing a date back out of a path
# ---------------------------------------------------------------------------


def test_parses_day_layout(tmp_path):
    path = tmp_path / "timeline" / "daily" / "2026-08" / "21.md"
    assert date_from_timeline_path(path) == date(2026, 8, 21)


def test_parses_date_layout(tmp_path):
    path = tmp_path / "timeline" / "daily" / "2026-08" / "2026-08-21.md"
    assert date_from_timeline_path(path) == date(2026, 8, 21)


def test_date_layout_ignores_a_mismatched_folder(tmp_path):
    """The filename is authoritative when it carries the whole date."""
    path = tmp_path / "timeline" / "daily" / "2026-01" / "2026-08-21.md"
    assert date_from_timeline_path(path) == date(2026, 8, 21)


def test_parses_legacy_structure(tmp_path):
    path = tmp_path / "timeline" / "2026-08" / "21.md"
    assert date_from_timeline_path(path) == date(2026, 8, 21)


@pytest.mark.parametrize(
    "relative",
    [
        "timeline/daily/2026-08/notes.md",
        "timeline/daily/notaMonth/21.md",
        "timeline/daily/2026-08/2026-13-01.md",  # impossible month
        "timeline/daily/2026-08/32.md",  # impossible day
        "timeline/daily/README.md",
    ],
)
def test_non_dated_files_return_none(tmp_path, relative):
    assert date_from_timeline_path(tmp_path / relative) is None


# ---------------------------------------------------------------------------
# Lookup accepts every layout
# ---------------------------------------------------------------------------


def test_resolves_day_layout(tmp_path):
    root = make_base(tmp_path)
    path = write_file(root, "2026-08", "21.md")

    assert Timeline.resolve_existing_file(root / "timeline", date(2026, 8, 21)) == path


def test_resolves_date_layout(tmp_path):
    root = make_base(tmp_path)
    path = write_file(root, "2026-08", "2026-08-21.md")

    assert Timeline.resolve_existing_file(root / "timeline", date(2026, 8, 21)) == path


def test_date_layout_wins_when_both_exist(tmp_path):
    """During a partial migration, prefer the newer naming."""
    root = make_base(tmp_path)
    write_file(root, "2026-08", "21.md")
    dated = write_file(root, "2026-08", "2026-08-21.md")

    assert Timeline.resolve_existing_file(root / "timeline", date(2026, 8, 21)) == dated


def test_resolves_none_when_absent(tmp_path):
    root = make_base(tmp_path)
    assert Timeline.resolve_existing_file(root / "timeline", date(2026, 8, 21)) is None


# ---------------------------------------------------------------------------
# Writing follows the configured layout
# ---------------------------------------------------------------------------


def test_new_files_use_the_configured_layout(tmp_path):
    root = make_base(tmp_path, layout="date")
    timeline = Timeline(root)

    _, path = timeline.record("hello")

    assert path.name == f"{date.today().strftime('%Y-%m-%d')}.md"


def test_new_files_default_to_day_layout(tmp_path):
    root = make_base(tmp_path)
    timeline = Timeline(root)

    _, path = timeline.record("hello")

    assert path.name == f"{date.today().strftime('%d')}.md"


def test_existing_file_is_appended_to_regardless_of_layout(tmp_path):
    """A day's entries must never split across two differently-named files."""
    root = make_base(tmp_path, layout="date")
    today = date.today()
    existing = write_file(root, today.strftime("%Y-%m"), f"{today.strftime('%d')}.md")

    timeline = Timeline(root)
    _, path = timeline.record("second entry")

    assert path == existing
    assert "second entry" in existing.read_text(encoding="utf-8")


def test_generated_header_is_correct_for_date_layout(tmp_path):
    root = make_base(tmp_path, layout="date")
    timeline = Timeline(root)

    _, path = timeline.record("hello")

    assert path.read_text(encoding="utf-8").startswith(
        f"# {date.today().strftime('%Y-%m-%d')} Timeline"
    )


def test_invalid_configured_layout_falls_back(tmp_path):
    root = make_base(tmp_path, layout="nonsense")
    assert Timeline(root).filename_layout == DEFAULT_FILENAME_LAYOUT


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def test_plan_renames_every_dated_file(tmp_path):
    root = make_base(tmp_path)
    for month in ("2026-01", "2026-02", "2026-08"):
        write_file(root, month, "21.md")

    moves, conflicts = plan_filename_migration(root / "timeline", "date")

    assert len(moves) == 3
    assert conflicts == []
    assert {t.name for _, t in moves} == {
        "2026-01-21.md",
        "2026-02-21.md",
        "2026-08-21.md",
    }


def test_plan_is_empty_when_already_migrated(tmp_path):
    root = make_base(tmp_path)
    write_file(root, "2026-08", "2026-08-21.md")

    moves, conflicts = plan_filename_migration(root / "timeline", "date")

    assert moves == []
    assert conflicts == []


def test_plan_reports_a_collision_instead_of_overwriting(tmp_path):
    root = make_base(tmp_path)
    write_file(root, "2026-08", "21.md", body="- 10:00 | day-named\n")
    write_file(root, "2026-08", "2026-08-21.md", body="- 11:00 | date-named\n")

    moves, conflicts = plan_filename_migration(root / "timeline", "date")

    assert moves == []
    assert len(conflicts) == 1


def test_plan_leaves_undated_files_alone(tmp_path):
    root = make_base(tmp_path)
    write_file(root, "2026-08", "21.md")
    (root / "timeline" / "daily" / "README.md").write_text("notes", encoding="utf-8")

    moves, _ = plan_filename_migration(root / "timeline", "date")

    assert len(moves) == 1
    assert (root / "timeline" / "daily" / "README.md").exists()


def test_plan_rejects_an_unknown_layout(tmp_path):
    root = make_base(tmp_path)

    with pytest.raises(TimelineError, match="Unknown filename layout"):
        plan_filename_migration(root / "timeline", "nonsense")


def test_apply_renames_and_preserves_content(tmp_path):
    root = make_base(tmp_path)
    source = write_file(root, "2026-08", "21.md", body="- 10:00 | keep me\n")
    original = source.read_text(encoding="utf-8")

    moves, _ = plan_filename_migration(root / "timeline", "date")
    apply_filename_migration(moves)

    target = root / "timeline" / "daily" / "2026-08" / "2026-08-21.md"
    assert not source.exists()
    assert target.read_text(encoding="utf-8") == original


def test_migration_round_trips(tmp_path):
    root = make_base(tmp_path)
    write_file(root, "2026-08", "21.md", body="- 10:00 | content\n")

    moves, _ = plan_filename_migration(root / "timeline", "date")
    apply_filename_migration(moves)
    moves_back, _ = plan_filename_migration(root / "timeline", "day")
    apply_filename_migration(moves_back)

    restored = root / "timeline" / "daily" / "2026-08" / "21.md"
    assert restored.exists()
    assert "content" in restored.read_text(encoding="utf-8")


def test_files_stay_in_their_month_folder(tmp_path):
    """Renaming must not reorganize the directory structure."""
    root = make_base(tmp_path)
    write_file(root, "2026-08", "21.md")

    moves, _ = plan_filename_migration(root / "timeline", "date")
    apply_filename_migration(moves)

    assert (root / "timeline" / "daily" / "2026-08" / "2026-08-21.md").exists()


@pytest.mark.parametrize("layout", FILENAME_LAYOUTS)
def test_timeline_is_readable_after_migrating_to_any_layout(tmp_path, layout):
    root = make_base(tmp_path)
    write_file(root, "2026-08", "21.md", body="- 10:00 | content\n")

    moves, _ = plan_filename_migration(root / "timeline", layout)
    apply_filename_migration(moves)
    clear_cache()

    found = Timeline.resolve_existing_file(root / "timeline", date(2026, 8, 21))
    assert found is not None
    assert "content" in found.read_text(encoding="utf-8")
