"""Tests for `mbase show --json`, the contract the Obsidian plugin depends on.

The plugin cannot use the base folder *name*: that name is relative to the
project root, while Obsidian needs paths relative to the vault root. When the
vault is the base folder itself those differ, which is what made module
navigation fail. Absolute paths are what let the plugin compute its own prefix.
"""

import json
import subprocess
import sys

import pytest

from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def run_base_json(cwd):
    """Run `mbase show --json` in cwd and parse the JSON line."""
    result = subprocess.run(
        [sys.executable, "-m", "memory_tool", "base", "show", "--json"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr

    # Scan backwards: notices may precede the JSON line.
    for line in reversed([l.strip() for l in result.stdout.splitlines() if l.strip()]):
        if line.startswith("{"):
            return json.loads(line)

    raise AssertionError(f"no JSON in output: {result.stdout!r}")


def make_base(root, name=".memory"):
    root.mkdir(parents=True, exist_ok=True)
    base = root if name == "." else root / name
    base.mkdir(parents=True, exist_ok=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (base / "timeline").mkdir(exist_ok=True)
    (base / "modules").mkdir(exist_ok=True)
    return base


def test_json_reports_absolute_paths(tmp_path):
    base = make_base(tmp_path, ".memory")
    data = run_base_json(tmp_path)

    assert data["base"] == str(base)
    assert data["root"] == str(tmp_path)
    assert data["base_name"] == ".memory"
    assert data["found"] is True


def test_json_from_inside_the_base_still_reports_the_base(tmp_path):
    """The Obsidian case: cwd is the vault root, which is the base folder.

    A plugin comparing base to its vault root gets an exact match here, and so
    correctly uses an empty prefix instead of appending ".memory" a second time.
    """
    base = make_base(tmp_path, ".memory")
    data = run_base_json(base)

    assert data["base"] == str(base)
    assert data["root"] == str(tmp_path)


def test_json_for_root_base(tmp_path):
    make_base(tmp_path, ".")
    write_pointer(tmp_path, ".")
    data = run_base_json(tmp_path)

    assert data["base"] == str(tmp_path)
    assert data["root"] == str(tmp_path)
    assert data["base_name"] == "."


def test_json_reports_nested_artifact_source(tmp_path):
    """The plugin warns the user when a stray nested base was ignored."""
    base = make_base(tmp_path, ".memory")
    stray = base / ".memory" / "timeline" / "daily" / "2026-08"
    stray.mkdir(parents=True)
    (stray / "13.md").write_text("- 00:31 | stray", encoding="utf-8")

    data = run_base_json(base)

    assert data["source"] == "nested-artifact"
    assert data["base"] == str(base)


def test_json_includes_content_subdirs(tmp_path):
    make_base(tmp_path, ".memory")
    data = run_base_json(tmp_path)

    assert "timeline" in data["content_subdirs"]
    assert "modules" in data["content_subdirs"]


def test_json_is_a_single_parseable_line(tmp_path):
    """Rich wrapping would corrupt the payload, so it must not be used here."""
    make_base(tmp_path, ".memory")
    result = subprocess.run(
        [sys.executable, "-m", "memory_tool", "base", "show", "--json"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    json_lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
    assert len(json_lines) == 1
    json.loads(json_lines[0])


def test_porcelain_prints_only_the_name(tmp_path):
    make_base(tmp_path, ".memory")
    result = subprocess.run(
        [sys.executable, "-m", "memory_tool", "base", "show", "--porcelain"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0
    assert result.stdout.strip().splitlines()[-1] == ".memory"
