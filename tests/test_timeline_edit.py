"""Tests for editing a timeline day: only the edited entries change.

All data is synthetic.
"""

from datetime import datetime

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.core.timeline import Timeline
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()

DAY = """# 2026-03-01 Timeline
Written before the first entry
- 09:00 | first
  a note about first
- 9:30 | second, written without a leading zero
- 13:00 | third
  a note about third

  after a blank line, still about third
"""


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    folder = tmp_path / ".memory"
    (folder / "timeline" / "daily" / "2026-03").mkdir(parents=True)
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield folder
    clear_cache()


@pytest.fixture
def day_file(base):
    path = base / "timeline" / "daily" / "2026-03" / "2026-03-01.md"
    path.write_text(DAY, encoding="utf-8")
    return path


def edit(*commands):
    return runner.invoke(app, ["edit", "2026-03-01"], input="".join(f"{c}\n" for c in commands))


def save(day_file, change):
    timeline = Timeline(day_file.parents[4])
    path, entries, date = timeline.parse_entries("2026-03-01")
    entries = change(entries)
    timeline.save_entries(path, entries, date)
    return day_file.read_text(encoding="utf-8")


def test_saving_without_changes_keeps_the_file(day_file):
    assert save(day_file, lambda entries: entries) == DAY


def test_editing_a_message_changes_only_that_line(day_file):
    def change(entries):
        entries[2]["message"] = "third, edited"
        return entries

    assert save(day_file, change) == DAY.replace("- 13:00 | third\n", "- 13:00 | third, edited\n")


def test_a_new_time_moves_the_entry_with_its_notes(day_file):
    def change(entries):
        entries[0]["time"] = "14:00"
        return entries

    assert save(day_file, change) == (
        "# 2026-03-01 Timeline\n"
        "Written before the first entry\n"
        "- 9:30 | second, written without a leading zero\n"
        "- 13:00 | third\n"
        "  a note about third\n"
        "\n"
        "  after a blank line, still about third\n"
        "- 14:00 | first\n"
        "  a note about first\n"
    )


def test_deleting_an_entry_keeps_its_notes_under_the_entry_before(day_file):
    text = save(day_file, lambda entries: [e for e in entries if e["message"] != "third"])

    assert "- 13:00 | third" not in text
    assert text.endswith(
        "- 9:30 | second, written without a leading zero\n"
        "  a note about third\n"
        "\n"
        "  after a blank line, still about third\n"
    )


def test_deleting_the_first_entry_keeps_its_notes_above_the_rest(day_file):
    text = save(day_file, lambda entries: entries[1:])

    assert text.startswith(
        "# 2026-03-01 Timeline\nWritten before the first entry\n  a note about first\n- 9:30 | second"
    )


def test_the_editor_deletes_with_confirmation_and_keeps_the_rest(day_file):
    result = edit("d 3", "y", "s")

    assert result.exit_code == 0, result.output
    text = day_file.read_text(encoding="utf-8")
    assert text.startswith("# 2026-03-01 Timeline\n")
    assert "- 13:00 | third" not in text
    assert "a note about third" in text
    assert "Written before the first entry" in text


def test_the_editor_without_saving_changes_nothing(day_file):
    edit("d 1", "y", "q", "y")

    assert day_file.read_text(encoding="utf-8") == DAY
