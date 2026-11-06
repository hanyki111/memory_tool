"""Arguments reach commands as written, on every platform. All data is synthetic.

On Windows, Click expands $VAR, %VAR% and wildcards in arguments read from the
command line unless told not to, so a recorded message could turn into file
names. These tests run the CLI as a real process to cover that start-up path.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def make_base(root: Path) -> Path:
    (root / ".memory-tool.yml").write_text('base: ".memory"\n', encoding="utf-8")
    base = root / ".memory"
    (base / "timeline").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    # Files a wildcard could match.
    (root / "a.py").write_text("", encoding="utf-8")
    (root / "b.py").write_text("", encoding="utf-8")
    return base


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONPATH": str(REPO), "PYTHONIOENCODING": "utf-8"}
    environment.pop("MEMORY_TOOL_ROOT", None)
    environment.pop("MEMORY_TOOL_BASE", None)
    return subprocess.run(
        [sys.executable, "-m", "memory_tool", *args],
        cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8",
    )


def test_a_recorded_message_is_not_expanded(tmp_path):
    base = make_base(tmp_path)
    message = "tidy *.py and $HOME and %USERNAME% and ~/x"

    result = run(tmp_path, "record", "--date", "2026-03-01", "--time", "09:05", "--", message)

    assert result.returncode == 0, result.stdout + result.stderr
    [day] = list((base / "timeline").rglob("*.md"))
    assert f"- 09:05 | {message}" in day.read_text(encoding="utf-8").splitlines()


def test_a_search_query_is_not_expanded(tmp_path):
    make_base(tmp_path)
    run(tmp_path, "record", "--date", "2026-03-01", "--time", "09:05", "--", "literal *.py here")

    result = run(tmp_path, "search", "*.py", "--no-cache", "--no-index", "--no-hybrid", "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"query": "*.py"' in result.stdout
