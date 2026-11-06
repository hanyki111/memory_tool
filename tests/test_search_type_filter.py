"""ms --type keeps results of that type. All data is synthetic."""

import json

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.search.filters import FileTypeFilter
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    folder = tmp_path / ".memory"
    (folder / "modules" / "demo").mkdir(parents=True)
    (folder / "timeline" / "daily" / "2026-03").mkdir(parents=True)
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (folder / "timeline" / "daily" / "2026-03" / "2026-03-01.md").write_text(
        "# 2026-03-01 Timeline\n- 09:05 | 합성 단어 기록\n", encoding="utf-8")
    (folder / "modules" / "demo" / "note.md").write_text("# Note\n합성 단어 문서\n", encoding="utf-8")
    clear_cache()
    yield tmp_path
    clear_cache()


def kinds(*args):
    result = runner.invoke(app, ["search", "--json", *args, "--", "합성"])
    reply = json.loads([line for line in result.output.splitlines() if line.strip()][-1])
    assert reply["ok"], reply
    return sorted(r["kind"] for r in reply["results"])


def test_type_timeline_keeps_timeline_results(base):
    assert kinds() == ["module", "timeline"]
    assert kinds("--type", "timeline") == ["timeline"]
    assert kinds("--type", "modules") == ["module"]


def test_matches_from_the_project_root_or_the_base_folder(base):
    day = base / ".memory" / "timeline" / "daily" / "2026-03" / "2026-03-01.md"
    assert FileTypeFilter.matches_type(day, "timeline", base)
    assert FileTypeFilter.matches_type(day, "timeline", base / ".memory")
    assert not FileTypeFilter.matches_type(day, "modules", base)


def test_cache_does_not_mix_knowledge_bases(tmp_path, monkeypatch):
    """The search cache lives in the home folder and is shared; one base must not see another's results."""
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    def make(name, text):
        root = tmp_path / name
        folder = root / ".memory"
        (folder / "timeline" / "daily" / "2026-03").mkdir(parents=True)
        (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
        (folder / "timeline" / "daily" / "2026-03" / "2026-03-01.md").write_text(
            f"# 2026-03-01 Timeline\n- 09:05 | 공통어 {text}\n", encoding="utf-8")
        write_pointer(root, ".memory")
        return root

    def search(root):
        monkeypatch.chdir(root)
        clear_cache()
        result = runner.invoke(app, ["search", "--json", "--", "공통어"])
        reply = json.loads([line for line in result.output.splitlines() if line.strip()][-1])
        return reply["cached"], [r["entry"]["text"] for r in reply["results"]]

    first, second = make("a", "첫째"), make("b", "둘째")
    assert search(first) == (False, ["공통어 첫째"])
    assert search(second) == (False, ["공통어 둘째"])
    assert search(first) == (True, ["공통어 첫째"])
    clear_cache()
