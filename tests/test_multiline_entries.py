"""Tests for entries of several lines, and for tags written before a message.

An entry's later lines are indented under its first line. All data is synthetic.
"""

import json
from datetime import date

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.core.timeline import (
    Timeline,
    clean_message,
    entry_at_line,
    parse_entry_lines,
    split_tags,
)
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
    (folder / "modules").mkdir(parents=True)
    (folder / "timeline" / "daily").mkdir(parents=True)
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield folder
    clear_cache()


def last_json(output):
    lines = [line for line in output.splitlines() if line.strip()]
    assert len(lines) == 1, output
    return json.loads(lines[0])


def record(*args):
    result = runner.invoke(app, ["record", *args, "--json"])
    assert result.exit_code == 0, result.output
    return last_json(result.output)


def today_file(base):
    return next((base / "timeline" / "daily").rglob("*.md"))


def write_day(base, day, body):
    folder = base / "timeline" / "daily" / f"{day:%Y-%m}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{day:%Y-%m-%d}.md"
    path.write_text(f"# {day:%Y-%m-%d} Timeline\n{body}", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


class TestCleanMessage:
    def test_drops_empty_lines_and_trailing_space(self):
        assert clean_message("  first  \r\n\n second \n\n") == "first\n second"

    def test_one_line_is_stripped(self):
        assert clean_message("  only  ") == "only"

    def test_empty(self):
        assert clean_message(" \n \n") == ""


class TestRecord:
    def test_later_lines_are_indented_under_the_first(self, base):
        data = record("첫째 줄\n둘째 줄\n\n  - 셋째 줄", "--time", "10:00")

        content = today_file(base).read_text(encoding="utf-8")
        assert content.endswith("- 10:00 | 첫째 줄\n  둘째 줄\n    - 셋째 줄\n")
        assert data["entry"]["text"] == "첫째 줄"
        assert data["entry"]["more"] == ["둘째 줄", "- 셋째 줄"]

    def test_tags_go_on_the_first_line(self, base):
        data = record("[버그] 로그인 오류\n원인은 세션 만료 #auth", "--time", "10:00")

        content = today_file(base).read_text(encoding="utf-8")
        assert content.endswith("- 10:00 | [버그] [auth] 로그인 오류\n  원인은 세션 만료\n")
        assert data["entry"]["tags"] == ["버그", "auth"]

    def test_hashtag_format_puts_tags_on_the_first_line(self, base):
        (base / "config.yaml").write_text("version: '1.0'\ntag:\n  storage_format: hashtag\n", encoding="utf-8")
        clear_cache()

        data = record("로그인 오류\n원인은 세션 만료 #auth", "--time", "10:00")

        content = today_file(base).read_text(encoding="utf-8")
        assert content.endswith("- 10:00 | 로그인 오류 #auth\n  원인은 세션 만료\n")
        assert data["entry"]["tags"] == ["auth"]

    def test_a_later_line_that_looks_like_an_entry_stays_part_of_it(self, base):
        record("회의\n- 09:00 | 이건 엔트리가 아님", "--time", "10:00")

        entries = parse_entry_lines(today_file(base).read_text(encoding="utf-8"))
        assert [(e["time"], e["text"], e["more"]) for e in entries] == [
            ("10:00", "회의", ["- 09:00 | 이건 엔트리가 아님"])
        ]

    def test_trailing_space_after_a_hashtag(self, base):
        data = record("끝 태그 #버그 ", "--time", "10:00")

        assert data["entry"]["text"] == "[버그] 끝 태그"
        assert data["entry"]["tags"] == ["버그"]


class TestLeadingHashtags:
    @pytest.mark.parametrize(
        "message, expected",
        [
            ("#버그 로그인 수정", ("로그인 수정", ["버그"], [])),
            ("#버그 #auth 로그인 수정", ("로그인 수정", ["버그", "auth"], [])),
            ("[버그] #auth 로그인 수정", ("로그인 수정", ["버그", "auth"], [])),
            ("#35 이슈 수정", ("#35 이슈 수정", [], [])),
            ("#35a 이슈 수정", ("이슈 수정", ["35a"], [])),
            ("#a/#b 수정", ("#a/#b 수정", [], [])),
            ("중간에 #버그 넣음", ("중간에 #버그 넣음", [], [])),
        ],
    )
    def test_split(self, message, expected):
        assert split_tags(message) == expected

    def test_recorded_in_the_configured_format(self, base):
        data = record("#버그 앞에 붙인 태그", "--time", "10:00")

        assert data["entry"]["text"] == "[버그] 앞에 붙인 태그"
        assert data["entry"]["tags"] == ["버그"]


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


DAY = (
    "- 09:00 | first\n"
    "  a later line of first\n"
    "a note written by hand\n"
    "  not a later line: the note came between\n"
    "- 10:00 | second\n"
    "\n"
    "  after a blank line\n"
)


class TestParse:
    def test_more_holds_the_later_lines(self):
        entries = parse_entry_lines(DAY)

        assert [(e["text"], e["more"]) for e in entries] == [
            ("first", ["a later line of first"]),
            ("second", []),
        ]

    @pytest.mark.parametrize("index, text", [(0, "first"), (1, "first"), (4, "second")])
    def test_entry_at_line(self, index, text):
        entry = entry_at_line(DAY.splitlines(), index)
        assert entry["text"] == text

    @pytest.mark.parametrize("index", [2, 3, 5, 6, 99])
    def test_no_entry_at_line(self, index):
        assert entry_at_line(DAY.splitlines(), index) is None


class TestMove:
    def test_moving_to_another_day_takes_the_later_lines(self, base):
        old = write_day(base, date(2026, 3, 1), "- 09:00 | 회의\n  안건 정리\n- 10:00 | 다음\n")

        Timeline().edit_entry("2026-03-01", "09:00", "회의", new_date="2026-03-02", force=True)

        [new] = [path for path in old.parent.glob("*.md") if path != old]
        assert new.read_text(encoding="utf-8").endswith("- 09:00 | 회의\n  안건 정리\n")
        assert "안건 정리" not in old.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------


def search(*args):
    result = runner.invoke(app, ["search", *args, "--no-cache", "--no-index", "--json"])
    return last_json(result.output)


class TestSearch:
    def test_a_hit_on_a_later_line_carries_its_entry(self, base):
        write_day(base, date(2026, 3, 1), "- 09:00 | 회의\n  포트 8443 결정\n")

        data = search("8443")

        [hit] = [item for item in data["results"] if item["kind"] == "timeline"]
        assert hit["entry"] == {
            "date": "2026-03-01", "time": "09:00", "text": "회의", "tags": [], "more": ["포트 8443 결정"],
        }

    def test_one_result_per_entry(self, base):
        write_day(base, date(2026, 3, 1), "- 09:00 | 8443 회의\n  8443 결정\n- 09:00 | 8443 회의\n")

        data = search("8443")

        timeline = [item for item in data["results"] if item["kind"] == "timeline"]
        assert [(item["entry"]["text"], item["entry"]["more"]) for item in timeline] == [
            ("8443 회의", ["8443 결정"]),
            ("8443 회의", []),
        ]
