"""Search reads the files; there is no SQLite index any more.

The index read only legacy module files and timeline paths, so when it matched
anything, such as a concept document, those few results replaced the file
search and hid module documents and recent entries. All data is synthetic.
"""

import json
from datetime import datetime

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
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
    (folder / "modules" / "topic").mkdir(parents=True)
    (folder / "concepts").mkdir()
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (folder / "concepts" / "idea.md").write_text("# Idea\n\nquokka in a concept\n", encoding="utf-8")
    (folder / "modules" / "topic" / "topic.md").write_text("# Topic\n\nquokka in a module\n", encoding="utf-8")
    clear_cache()
    yield folder
    clear_cache()


def found_files(*args):
    result = runner.invoke(app, ["search", "quokka", "--no-cache", "--no-hybrid", "--json", *args])
    assert result.exit_code == 0, result.output
    return {item["path"].replace("\\", "/").split(".memory/")[-1] for item in json.loads(result.output)["results"]}


def test_module_documents_and_recent_entries_are_found_beside_concepts(base):
    runner.invoke(app, ["record", "quokka in today's entry"])

    files = found_files()

    assert "concepts/idea.md" in files
    assert "modules/topic/topic.md" in files
    assert any(path.startswith("timeline/") for path in files)


def test_no_index_is_still_accepted(base):
    assert found_files("--no-index") == found_files()


def test_recording_creates_no_index(base):
    runner.invoke(app, ["record", "an entry"])

    assert not (base / ".index.db").exists()


def test_the_index_command_is_gone(base):
    assert runner.invoke(app, ["index", "--stats"]).exit_code != 0
