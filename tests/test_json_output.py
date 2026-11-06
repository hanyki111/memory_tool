"""Tests for --json output: entries, views, recording, search and AI commands.

All data is synthetic.
"""

import io
import json
from datetime import date, datetime, timedelta

import pytest
from typer.testing import CliRunner

from memory_tool.commands import json_output
from memory_tool.commands.common import app
from memory_tool.core.timeline import Timeline, entry_tags, parse_entry_lines, split_tags
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


@pytest.fixture
def base(tmp_path, monkeypatch):
    """A knowledge base in .memory, with the working directory at its project."""
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


def write_day(base, day, body, layout="date"):
    folder = base / "timeline" / "daily" / f"{day:%Y-%m}"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{day:%Y-%m-%d}.md" if layout == "date" else f"{day:%d}.md"
    path = folder / name
    path.write_text(f"# {day:%Y-%m-%d} Timeline\n{body}", encoding="utf-8")
    return path


def last_json(output):
    """The result line. It must be the only line of output."""
    lines = [line for line in output.splitlines() if line.strip()]
    assert len(lines) == 1, output
    return json.loads(lines[0])


# ---------------------------------------------------------------------------
# Reading entries
# ---------------------------------------------------------------------------


class TestTags:
    def test_reads_leading_brackets(self):
        assert split_tags("[버그][긴급] 로그인 오류") == ("로그인 오류", ["버그", "긴급"], [])

    def test_reads_spaced_brackets_as_recorded(self):
        assert split_tags("[bug] [auth] Fixed login") == ("Fixed login", ["bug", "auth"], [])

    def test_reads_trailing_hashtags(self):
        assert split_tags("포트 변경 #설정 #서버") == ("포트 변경", [], ["설정", "서버"])

    def test_ignores_tags_in_the_middle(self):
        assert split_tags("issue #12 and [draft] notes") == ("issue #12 and [draft] notes", [], [])

    def test_entry_tags_have_no_duplicates(self):
        assert entry_tags("[설정] 포트 변경 #설정 #서버") == ["설정", "서버"]


class TestParseEntryLines:
    def test_keeps_text_as_written(self):
        content = "# T\n- 14:30 | [버그] 로그인 오류 수정\n- 9:05 | 포트 변경 #설정\n"

        assert parse_entry_lines(content) == [
            {"time": "14:30", "text": "[버그] 로그인 오류 수정", "tags": ["버그"]},
            {"time": "9:05", "text": "포트 변경 #설정", "tags": ["설정"]},
        ]

    def test_leaves_out_lines_that_are_not_entries(self):
        content = "# T\n- 10:00 | entry\nA note written by hand\n- not an entry\n"

        assert [entry["text"] for entry in parse_entry_lines(content)] == ["entry"]


class TestGetRange:
    def test_reads_both_layouts_oldest_first(self, base):
        write_day(base, date(2026, 3, 2), "- 10:00 | second\n", layout="day")
        write_day(base, date(2026, 3, 1), "- 10:00 | first\n", layout="date")

        days = Timeline(base.parent).get_range(date(2026, 3, 1), date(2026, 3, 3))

        assert [(day.date(), "first" in content or "second" in content) for day, _, content in days] == [
            (date(2026, 3, 1), True),
            (date(2026, 3, 2), True),
        ]
        assert days[1][1].name == "02.md"

    def test_both_ends_are_included_and_time_is_ignored(self, base):
        write_day(base, date(2026, 3, 1), "- 10:00 | a\n")
        write_day(base, date(2026, 3, 3), "- 10:00 | b\n")

        days = Timeline(base.parent).get_range(datetime(2026, 3, 1, 23, 59), datetime(2026, 3, 3, 0, 0))

        assert len(days) == 2

    def test_empty_period(self, base):
        assert Timeline(base.parent).get_range(date(2026, 3, 1), date(2026, 3, 5)) == []


# ---------------------------------------------------------------------------
# The shared output
# ---------------------------------------------------------------------------


class TestEmit:
    def test_one_utf8_line_even_when_the_locale_is_not(self, monkeypatch):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp949")
        monkeypatch.setattr("sys.stdout", stream)

        json_output.emit({"text": "한글 ✓", "long": "x" * 500})

        line = raw.getvalue().decode("utf-8")
        assert line.count("\n") == 1
        assert json.loads(line) == {"text": "한글 ✓", "long": "x" * 500}

    def test_failure_carries_a_code_and_exits(self, capsys):
        with pytest.raises(SystemExit) as raised:
            json_output.fail(json_output.NOT_FOUND, "No such module", name="x")

        assert raised.value.code == 1
        assert json.loads(capsys.readouterr().out) == {
            "ok": False, "code": "not_found", "error": "No such module", "name": "x",
        }

    def test_day_keeps_content_that_entries_leave_out(self, tmp_path):
        content = "# T\n- 10:00 | [a] entry\nhand-written note\n"

        day = json_output.day_dict(date(2026, 3, 1), tmp_path / "01.md", content)

        assert day["entries"] == [{"date": "2026-03-01", "time": "10:00", "text": "[a] entry", "tags": ["a"]}]
        assert "hand-written note" in day["content"]
        assert day["path"] == str((tmp_path / "01.md").resolve())


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def view(*args):
    result = runner.invoke(app, list(args))
    return result, last_json(result.output)


class TestViews:
    def test_today(self, base):
        now = datetime.now()
        write_day(base, now, "- 08:00 | [작업] 아침 기록\n손으로 적은 메모\n")

        result, data = view("today", "--json")

        assert result.exit_code == 0
        assert data["ok"] is True
        assert data["from"] == data["to"] == f"{now:%Y-%m-%d}"
        [day] = data["days"]
        assert day["entries"] == [{"date": f"{now:%Y-%m-%d}", "time": "08:00", "text": "[작업] 아침 기록", "tags": ["작업"]}]
        assert "손으로 적은 메모" in day["content"]

    def test_today_without_entries_is_an_empty_list(self, base):
        result, data = view("today", "--json")

        assert result.exit_code == 0
        assert data["ok"] is True and data["days"] == []

    def test_period_reads_both_layouts(self, base):
        write_day(base, date(2026, 3, 1), "- 10:00 | a\n", layout="day")
        write_day(base, date(2026, 3, 3), "- 10:00 | b\n", layout="date")
        write_day(base, date(2026, 3, 4), "- 10:00 | outside\n")

        _, data = view("days", "--from", "2026-03-01", "--to", "2026-03-03", "--json")

        assert (data["from"], data["to"]) == ("2026-03-01", "2026-03-03")
        assert [day["date"] for day in data["days"]] == ["2026-03-01", "2026-03-03"]

    def test_to_alone_counts_back_the_number_of_days(self, base):
        _, data = view("days", "3", "--to", "2026-03-10", "--json")

        assert (data["from"], data["to"]) == ("2026-03-08", "2026-03-10")

    @pytest.mark.parametrize("args", [
        ("--from", "2026-03-05", "--to", "2026-03-01"),
        ("--from", "03-05"),
        ("0",),
    ])
    def test_bad_period_is_invalid_argument(self, base, args):
        result, data = view("days", *args, "--json")

        assert result.exit_code == 1
        assert data["ok"] is False and data["code"] == "invalid_argument"

    def test_day(self, base):
        write_day(base, date(2026, 3, 1), "- 10:00 | a #태그\n", layout="day")

        _, data = view("day", "2026-03-01", "--json")

        assert data["days"][0]["entries"][0]["tags"] == ["태그"]

    def test_day_with_a_bad_date(self, base):
        result, data = view("day", "nonsense", "--json")

        assert result.exit_code == 1 and data["code"] == "invalid_argument"

    @pytest.mark.parametrize("command", ["week", "month"])
    def test_week_and_month(self, base, command):
        now = datetime.now()
        write_day(base, now, "- 08:00 | 기록\n")

        _, data = view(command, "--json")

        assert data["to"] == f"{now:%Y-%m-%d}"
        assert [day["date"] for day in data["days"]] == [f"{now:%Y-%m-%d}"]

    def test_people_still_get_text(self, base):
        write_day(base, date(2026, 3, 1), "- 10:00 | a\n")

        result = runner.invoke(app, ["days", "--from", "2026-03-01", "--to", "2026-03-02"])

        assert result.exit_code == 0
        assert "2026-03-01 ~ 2026-03-02" in result.output
        assert "1 day(s) with entries in this period" in result.output
