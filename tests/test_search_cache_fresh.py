"""Search never returns results from before an edit. All data is synthetic."""

import json
import os

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.search.cache import content_stamp
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    root = tmp_path / "project"
    folder = root / ".memory"
    (folder / "timeline" / "daily" / "2026-03").mkdir(parents=True)
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (folder / "timeline" / "daily" / "2026-03" / "2026-03-01.md").write_text(
        "# 2026-03-01 Timeline\n- 09:05 | 합성어 첫 기록\n", encoding="utf-8")
    write_pointer(root, ".memory")
    monkeypatch.chdir(root)
    clear_cache()
    yield folder
    clear_cache()


def found(*args):
    result = runner.invoke(app, ["search", "--json", *args, "--", "합성어"])
    reply = json.loads([line for line in result.output.splitlines() if line.strip()][-1])
    assert reply["ok"], reply
    return reply["cached"], sorted(r["entry"]["text"] for r in reply["results"])


def test_keyword_search_sees_an_entry_recorded_just_before(base):
    assert found() == (False, ["합성어 첫 기록"])
    # Another day: neighbouring lines of one file are merged into one result.
    result = runner.invoke(app, ["record", "--date", "2026-03-05", "--time", "10:00", "--", "합성어 둘째 기록"])
    assert result.exit_code == 0, result.output
    assert found() == (False, ["합성어 둘째 기록", "합성어 첫 기록"])


def test_keyword_search_sees_an_edit_by_hand(base):
    assert found() == (False, ["합성어 첫 기록"])
    day = base / "timeline" / "daily" / "2026-03" / "2026-03-01.md"
    day.write_text("# 2026-03-01 Timeline\n- 09:05 | 합성어 손으로 고친 기록\n", encoding="utf-8")
    assert found() == (False, ["합성어 손으로 고친 기록"])


def test_the_stamp_follows_every_change(tmp_path):
    folder = tmp_path / "kb"
    (folder / "a").mkdir(parents=True)
    note = folder / "a" / "note.md"
    note.write_text("one", encoding="utf-8")
    (folder / "a" / "image.png").write_bytes(b"x")
    first = content_stamp([folder])
    assert content_stamp([folder]) == first, "no change, same stamp"

    (folder / "a" / "image.png").write_bytes(b"other")
    assert content_stamp([folder]) == first, "only Markdown counts"

    note.write_text("two", encoding="utf-8")
    os.utime(note, ns=(1, 1_000_000_000))
    edited = content_stamp([folder])
    assert edited != first

    (folder / "a" / "new.md").write_text("new", encoding="utf-8")
    added = content_stamp([folder])
    assert added != edited

    (folder / "a" / "new.md").rename(folder / "a" / "renamed.md")
    renamed = content_stamp([folder])
    assert renamed != added

    (folder / "a" / "renamed.md").unlink()
    assert content_stamp([folder]) not in (added, renamed)


def test_the_stamp_skips_what_it_cannot_read(tmp_path):
    folder = tmp_path / "kb"
    folder.mkdir()
    (folder / "note.md").write_text("one", encoding="utf-8")
    assert content_stamp([folder, tmp_path / "missing"]) == content_stamp([folder])
