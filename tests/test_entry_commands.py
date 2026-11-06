"""Tests for entry find/edit/delete, which programs use to change one entry.

All data is synthetic.
"""

import json
from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.core.timeline import EntryNotFound, Timeline
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


YESTERDAY = datetime.now() - timedelta(days=1)
DAY = YESTERDAY.strftime("%Y-%m-%d")
OTHER = (YESTERDAY - timedelta(days=1)).strftime("%Y-%m-%d")


def day_file(base, day):
    """The day's file, in whichever layout it was written; new files use the configured one."""
    when = datetime.strptime(day, "%Y-%m-%d")
    found = Timeline.resolve_existing_file(base / "timeline", when)
    return found or base / "timeline" / "daily" / f"{when:%Y-%m}" / f"{when:%Y-%m-%d}.md"


def write_day(base, day, body):
    path = day_file(base, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {day} Timeline\n{body}", encoding="utf-8")
    return path


def run(*args):
    result = runner.invoke(app, ["entry", *args, "--json"])
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 1, result.output
    return json.loads(lines[0]), result.exit_code


BODY = (
    "- 09:00 | [버그] [긴급] 로그인 오류\n"
    "  손으로 적은 메모\n"
    "- 10:30 | 회의 정리\n"
    "- 10:30 | 회의 정리\n"
    "- 11:00 | 따옴표 \"큰\" '작은' $HOME\n"
)


class TestFind:
    def test_finds_as_written(self, base):
        write_day(base, DAY, BODY)
        reply, code = run("find", "--date", DAY, "--time", "11:00", "--text", "따옴표 \"큰\" '작은' $HOME")
        assert code == 0
        assert reply["found"] is True
        assert reply["entry"]["time"] == "11:00"

    @pytest.mark.parametrize("typed", ["[버그][긴급] 로그인 오류", "로그인 오류 #버그 #긴급", "[버그] 로그인 오류 #긴급"])
    def test_finds_tags_as_typed(self, base, typed):
        """record rewrites tags, so the phone's check must find what it typed."""
        write_day(base, DAY, BODY)
        reply, _ = run("find", "--date", DAY, "--time", "9:00", "--text", typed)
        assert reply["found"] is True
        assert reply["entry"]["text"] == "[버그] [긴급] 로그인 오류"
        assert reply["entry"]["tags"] == ["버그", "긴급"]

    def test_finds_what_record_wrote(self, base):
        write_day(base, DAY, "")
        record = runner.invoke(app, ["record", "--json", "--date", DAY, "--time", "08:15", "--", "끝 태그 #idea #work"])
        assert record.exit_code == 0, record.output
        reply, _ = run("find", "--date", DAY, "--time", "08:15", "--text", "끝 태그 #idea #work")
        assert reply["found"] is True

    def test_not_there(self, base):
        write_day(base, DAY, BODY)
        assert run("find", "--date", DAY, "--time", "11:01", "--text", "회의 정리")[0] == {"ok": True, "found": False}
        assert run("find", "--date", DAY, "--time", "10:30", "--text", "다른 글")[0]["found"] is False
        assert run("find", "--date", OTHER, "--time", "10:30", "--text", "회의 정리")[0]["found"] is False

    def test_bad_date(self, base):
        reply, code = run("find", "--date", "11-07", "--time", "10:30", "--text", "x")
        assert code == 1
        assert reply["code"] == "invalid_argument"


class TestEdit:
    def test_changes_text_and_keeps_the_rest(self, base):
        path = write_day(base, DAY, BODY)
        reply, code = run("edit", "--date", DAY, "--time", "09:00", "--text", "[버그] [긴급] 로그인 오류",
                          "--new-text", "로그인 오류 수정 #버그")
        assert code == 0
        assert reply["entry"] == {"date": DAY, "time": "09:00", "text": "[버그] 로그인 오류 수정", "tags": ["버그"]}
        assert reply["previous"]["text"] == "[버그] [긴급] 로그인 오류"
        content = path.read_text(encoding="utf-8")
        assert "- 09:00 | [버그] 로그인 오류 수정\n  손으로 적은 메모\n" in content
        assert content.count("회의 정리") == 2

    def test_time_change_reorders_and_moves_hand_lines(self, base):
        path = write_day(base, DAY, BODY)
        run("edit", "--date", DAY, "--time", "09:00", "--text", "[버그] [긴급] 로그인 오류", "--new-time", "12:00")
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[-2:] == ["- 12:00 | [버그] [긴급] 로그인 오류", "  손으로 적은 메모"]

    def test_text_starting_with_a_dash(self, base):
        path = write_day(base, DAY, BODY)
        reply, code = run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-text=-대시로 시작")
        assert code == 0, reply
        content = path.read_text(encoding="utf-8")
        assert "- 10:30 | -대시로 시작\n" in content
        assert content.count("회의 정리") == 1, "only the first of two identical entries changes"

    def test_moves_to_another_day(self, base):
        source = write_day(base, DAY, BODY)
        write_day(base, OTHER, "- 08:00 | 그날 아침\n- 23:00 | 그날 밤\n")
        reply, code = run("edit", "--date", DAY, "--time", "11:00", "--text", "따옴표 \"큰\" '작은' $HOME",
                          "--new-date", OTHER, "--new-time", "22:00")
        assert code == 0
        assert reply["entry"]["date"] == OTHER
        assert "따옴표" not in source.read_text(encoding="utf-8")
        assert day_file(base, OTHER).read_text(encoding="utf-8").splitlines()[1:] == [
            "- 08:00 | 그날 아침", "- 22:00 | 따옴표 \"큰\" '작은' $HOME", "- 23:00 | 그날 밤",
        ]

    def test_moves_to_a_day_without_a_file(self, base):
        write_day(base, DAY, BODY)
        run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-date", OTHER)
        assert day_file(base, OTHER).read_text(encoding="utf-8") == f"# {OTHER} Timeline\n- 10:30 | 회의 정리\n"

    def test_not_found_changes_nothing(self, base):
        path = write_day(base, DAY, BODY)
        reply, code = run("edit", "--date", DAY, "--time", "09:00", "--text", "이미 바뀐 글", "--new-text", "x")
        assert code == 1
        assert reply["code"] == "not_found"
        assert path.read_text(encoding="utf-8") == f"# {DAY} Timeline\n{BODY}"

    def test_future_time_is_refused(self, base):
        write_day(base, DAY, BODY)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        reply, code = run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-date", tomorrow)
        assert code == 1
        assert reply["code"] == "future_time"

    def test_distant_past_needs_force(self, base):
        write_day(base, DAY, BODY)
        old = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        reply, _ = run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-date", old)
        assert reply["code"] == "distant_past"
        reply, code = run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-date", old, "--force")
        assert code == 0
        assert reply["entry"]["date"] == old

    def test_old_entry_text_can_change_without_force(self, base):
        old = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        write_day(base, old, "- 10:00 | 오래된 기록\n")
        reply, code = run("edit", "--date", old, "--time", "10:00", "--text", "오래된 기록", "--new-text", "고친 기록")
        assert code == 0, reply

    @pytest.mark.parametrize("empty", ["   ", "[태그만]"])
    def test_empty_text_is_refused(self, base, empty):
        write_day(base, DAY, BODY)
        reply, code = run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-text", empty)
        assert code == 1
        assert reply["code"] == "invalid_argument"

    def test_bad_new_time(self, base):
        write_day(base, DAY, BODY)
        reply, _ = run("edit", "--date", DAY, "--time", "10:30", "--text", "회의 정리", "--new-time", "25:00")
        assert reply["code"] == "invalid_argument"


class TestDelete:
    def test_deletes_and_keeps_hand_lines(self, base):
        path = write_day(base, DAY, BODY)
        reply, code = run("delete", "--date", DAY, "--time", "09:00", "--text", "로그인 오류 #버그 #긴급")
        assert code == 0
        assert reply["entry"]["text"] == "[버그] [긴급] 로그인 오류"
        content = path.read_text(encoding="utf-8")
        assert "로그인 오류" not in content
        assert "  손으로 적은 메모" in content

    def test_not_found(self, base):
        write_day(base, DAY, BODY)
        reply, code = run("delete", "--date", DAY, "--time", "09:01", "--text", "회의 정리")
        assert code == 1
        assert reply["code"] == "not_found"


class TestNormalize:
    def test_is_idempotent(self, base):
        timeline = Timeline()
        for typed in ["[a][b] x", "x #a #b", "plain  two  spaces", "issue #12 in the middle"]:
            once = timeline.normalize_text(typed)
            assert timeline.normalize_text(once) == once

    def test_joins_lines(self, base):
        assert Timeline().normalize_text("a\r\nb\n") == "a b"

    def test_api_raises_not_found(self, base):
        write_day(base, DAY, BODY)
        with pytest.raises(EntryNotFound):
            Timeline().delete_entry(DAY, "10:30", "없음")
