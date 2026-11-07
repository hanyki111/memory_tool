"""ms --json returns every matching entry, also neighbouring ones. All data is synthetic."""

import json

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()

DAY = """# 2026-03-01 Timeline
- 09:00 | 합성어 하나
- 09:10 | 합성어 둘
- 09:20 | 다른 기록
- 09:30 | 합성어 셋
"""


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
    (folder / "timeline" / "daily" / "2026-03" / "2026-03-01.md").write_text(DAY, encoding="utf-8")
    write_pointer(root, ".memory")
    monkeypatch.chdir(root)
    clear_cache()
    yield folder
    clear_cache()


def entries(*args):
    result = runner.invoke(app, ["search", "--json", *args, "--", "합성어"])
    reply = json.loads([line for line in result.output.splitlines() if line.strip()][-1])
    assert reply["ok"], reply
    return sorted(r["entry"]["time"] for r in reply["results"])


@pytest.mark.parametrize("args", [(), ("--no-index",), ("--type", "timeline")])
def test_neighbouring_entries_each_come_back(base, args):
    assert entries(*args) == ["09:00", "09:10", "09:30"]


def test_max_still_limits(base):
    assert len(entries("--max", "2")) == 2


def test_the_screen_still_shows_the_matches(base):
    result = runner.invoke(app, ["search", "--", "합성어"])
    assert result.exit_code == 0, result.output
    assert "합성어 하나" in result.output and "합성어 셋" in result.output
