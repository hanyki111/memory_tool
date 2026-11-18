"""Tests for mplan: daily plans for people and programs, and fixes to weekly and monthly plans.

All data is synthetic.
"""

import json
from datetime import date, datetime, timedelta

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.core.timeline import parse_entry_lines
from memory_tool.planner import DailyPlan, MonthlyPlan, WeeklyPlan
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    folder = tmp_path / ".memory"
    (folder / "timeline" / "daily").mkdir(parents=True)
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield folder
    clear_cache()


def plan(*args):
    return runner.invoke(app, ["plan", *args])


def plan_json(*args):
    result = plan(*args, "--json")
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 1, result.output
    return json.loads(lines[0]), result.exit_code


def write_daily(base, day, tasks):
    path = base / "plans" / "daily" / f"{day:%Y-%m}" / f"{day:%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(tasks)
    path.write_text(
        f"# Daily Plan: {day:%Y-%m-%d}\n\n## Today's Goals\n\n{body}\n\n## Progress\n\n**Progress:** 0/0 (0%)\n",
        encoding="utf-8",
    )
    return path


def timeline_entries(base, day=TODAY):
    files = [p for p in (base / "timeline").rglob("*.md")]
    text = "".join(p.read_text(encoding="utf-8") for p in files if day.strftime("%d") in p.stem)
    return parse_entry_lines(text)


def snapshot(folder):
    return {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()} | {
        str(p): None for p in folder.rglob("*") if p.is_dir()
    }


# ---------------------------------------------------------------------------
# 1. Numbers: the listed number is the one done takes
# ---------------------------------------------------------------------------


class TestNumbers:
    def test_daily_numbers_count_incomplete_tasks(self, base):
        write_daily(base, TODAY, ["- [x] 끝낸 일 [09:00]", "- [ ] 남은 일", "- [ ] 또 남은 일"])

        tasks = DailyPlan(base).get_tasks(incomplete_only=True)
        assert [(t["index"], t["text"]) for t in tasks] == [(1, "남은 일"), (2, "또 남은 일")]

        result = plan("daily", "done", "2")
        assert result.exit_code == 0, result.output
        assert "- [x] 또 남은 일" in result.output

    def test_the_not_found_list_offers_numbers_done_accepts(self, base):
        write_daily(base, TODAY, ["- [x] 끝낸 일 [09:00]", "- [ ] 남은 일"])

        result = plan("daily", "done", "없는 일")
        assert "1. 남은 일" in result.output
        assert plan("daily", "done", "1").exit_code == 0

    def test_an_empty_checkbox_is_not_a_task(self, base):
        write_daily(base, TODAY, ["- [ ]", "- [ ] 일"])
        assert [t["text"] for t in DailyPlan(base).get_tasks()] == ["일"]

    def test_weekly_numbers_count_incomplete_goals(self, base):
        weekly = WeeklyPlan(base)
        weekly.add_goal("둘째 목표")
        weekly.add_goal("첫째 목표")
        assert weekly.mark_done("1")[0]

        goals = weekly.get_goals(incomplete_only=True)
        assert [(g["index"], g["text"]) for g in goals] == [(1, "둘째 목표")]

        result = plan("weekly", "done", "1")
        assert result.exit_code == 0, result.output
        assert "- [x] 둘째 목표" in result.output


# ---------------------------------------------------------------------------
# 2. Output keeps [x] and other brackets
# ---------------------------------------------------------------------------


class TestOutput:
    def test_daily_done_shows_the_checkbox(self, base):
        plan("daily", "add", "[auth] 로그인")
        result = plan("daily", "done", "1")
        assert "- [x] [auth] 로그인" in result.output

    def test_monthly_done_shows_the_checkbox(self, base):
        plan("monthly", "add", "월간 목표")
        result = plan("monthly", "done", "월간 목표")
        assert result.exit_code == 0, result.output
        assert "- [x] 월간 목표" in result.output

    def test_show_keeps_brackets_in_tasks(self, base):
        write_daily(base, TODAY, ["- [ ] [auth] 로그인"])
        assert "[auth] 로그인" in plan("daily").output


# ---------------------------------------------------------------------------
# 3. Showing changes nothing on disk
# ---------------------------------------------------------------------------


class TestShowReadsOnly:
    @pytest.mark.parametrize("args", [["daily"], ["daily", "show", "2020-01-01"], ["weekly"], ["monthly"]])
    def test_no_plan_creates_nothing(self, base, args):
        before = snapshot(base)
        plan(*args)
        assert snapshot(base) == before

    def test_stale_progress_is_shown_but_not_written(self, base):
        path = write_daily(base, TODAY, ["- [x] 끝낸 일 [09:00]", "- [ ] 남은 일"])
        before = path.read_text(encoding="utf-8")

        result = plan("daily")

        assert "1/2 (50%)" in result.output
        assert path.read_text(encoding="utf-8") == before

    def test_json_show_writes_nothing(self, base):
        write_daily(base, TODAY, ["- [ ] 일"])
        before = snapshot(base)
        plan_json("daily", "show")
        assert snapshot(base) == before


# ---------------------------------------------------------------------------
# 4. The template's timeline link follows the filename layout
# ---------------------------------------------------------------------------


class TestTimelineLink:
    @pytest.mark.parametrize("layout, name", [("day", f"{TODAY:%d}.md"), ("date", f"{TODAY:%Y-%m-%d}.md")])
    def test_link_names_the_file_as_configured(self, base, layout, name):
        (base / "config.yaml").write_text(f"version: '1.0'\ntimeline:\n  filename: {layout}\n", encoding="utf-8")
        clear_cache()

        path = DailyPlan(base).create_plan()

        assert f"(../../../timeline/daily/{TODAY:%Y-%m}/{name})" in path.read_text(encoding="utf-8")

    def test_link_points_at_an_existing_file(self, base):
        existing = base / "timeline" / "daily" / f"{TODAY:%Y-%m}" / f"{TODAY:%Y-%m-%d}.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("# Timeline\n", encoding="utf-8")

        path = DailyPlan(base).create_plan()

        assert f"{TODAY:%Y-%m-%d}.md)" in path.read_text(encoding="utf-8")

    def test_a_template_can_use_the_link(self, base):
        template = base / "plans" / "daily" / "templates" / "daily.md"
        template.parent.mkdir(parents=True)
        template.write_text("# {date}\n[timeline]({timeline})\n", encoding="utf-8")

        path = DailyPlan(base).create_plan()

        assert path.read_text(encoding="utf-8").endswith(f"/{TODAY:%d}.md)\n")


# ---------------------------------------------------------------------------
# 5. --json
# ---------------------------------------------------------------------------


class TestJson:
    def test_show(self, base):
        write_daily(base, TODAY, ["- [ ] 남은 일", "- [x] 끝낸 일 [9:05]"])
        (base / "plans" / "recurring.md").write_text("# Recurring\n- 환율 확인\n", encoding="utf-8")

        data, code = plan_json("daily")

        assert code == 0
        assert data["ok"] is True
        assert data["date"] == f"{TODAY:%Y-%m-%d}"
        assert data["exists"] is True
        assert data["tasks"] == [
            {"line": 5, "text": "남은 일", "done": False, "time": None},
            {"line": 6, "text": "끝낸 일", "done": True, "time": "09:05"},
        ]
        assert data["progress"] == {"done": 1, "total": 2}
        assert data["recurring"] == "# Recurring\n- 환율 확인"

    def test_show_another_day(self, base):
        write_daily(base, YESTERDAY, ["- [ ] 어제 일"])

        for args in (["daily", "yesterday"], ["daily", "show", "yesterday"], ["daily", f"{YESTERDAY:%Y-%m-%d}"]):
            data, _ = plan_json(*args)
            assert data["date"] == f"{YESTERDAY:%Y-%m-%d}"
            assert [t["text"] for t in data["tasks"]] == ["어제 일"]

    def test_show_without_a_plan(self, base):
        data, code = plan_json("daily")
        assert code == 0
        assert (data["exists"], data["tasks"]) == (False, [])

    def test_add(self, base):
        data, code = plan_json("daily", "add", "새\n작업")

        assert code == 0
        assert data["task"]["text"] == "새 작업"
        assert data["task"]["done"] is False
        assert data["plan"]["tasks"] == [data["task"]]

    def test_done_records_to_the_timeline(self, base):
        plan("daily", "add", "작업")
        [task] = plan_json("daily")[0]["tasks"]

        data, code = plan_json("daily", "done", "작업", "--line", str(task["line"]))

        assert code == 0
        assert data["task"]["done"] is True
        assert data["timeline"] == {"date": f"{TODAY:%Y-%m-%d}", "time": data["task"]["time"], "text": "✓ 작업 (Daily Plan)"}
        assert [e["text"] for e in timeline_entries(base)] == ["✓ 작업 (Daily Plan)"]

    def test_errors_are_json(self, base):
        data, code = plan_json("daily", "done", "없는 일")
        assert (code, data["ok"], data["code"]) == (1, False, "not_found")

        data, code = plan_json("daily", "add")
        assert (code, data["code"]) == (1, "invalid_argument")

        data, code = plan_json("weekly")
        assert (code, data["code"]) == (1, "invalid_argument")

    def test_ambiguous(self, base):
        write_daily(base, TODAY, ["- [ ] 문서 쓰기", "- [ ] 문서 읽기"])
        data, code = plan_json("daily", "done", "문서")
        assert (code, data["code"]) == (1, "invalid_argument")


# ---------------------------------------------------------------------------
# 6. --line: changes only the task that is still on that line
# ---------------------------------------------------------------------------


class TestLine:
    def test_a_moved_task_is_not_found(self, base):
        path = write_daily(base, TODAY, ["- [ ] 작업"])
        before = path.read_text(encoding="utf-8")

        data, code = plan_json("daily", "done", "작업", "--line", "4")

        assert (code, data["code"]) == (1, "not_found")
        assert path.read_text(encoding="utf-8") == before

    def test_other_text_on_the_line_is_not_found(self, base):
        path = write_daily(base, TODAY, ["- [ ] 다른 작업"])
        before = path.read_text(encoding="utf-8")

        data, code = plan_json("daily", "done", "작업", "--line", "5")

        assert (code, data["code"]) == (1, "not_found")
        assert path.read_text(encoding="utf-8") == before

    def test_the_same_text_twice_takes_the_one_on_the_line(self, base):
        path = write_daily(base, TODAY, ["- [ ] 같은 일", "- [ ] 같은 일"])

        plan_json("daily", "done", "같은 일", "--line", "6")

        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[4] == "- [ ] 같은 일"
        assert lines[5].startswith("- [x] 같은 일 [")


# ---------------------------------------------------------------------------
# 7. undo
# ---------------------------------------------------------------------------


class TestUndo:
    def test_undo_reopens_and_deletes_the_timeline_entry(self, base):
        plan("daily", "add", "작업")
        plan("daily", "done", "작업")
        [task] = plan_json("daily")[0]["tasks"]

        data, code = plan_json("daily", "undo", "작업", "--line", str(task["line"]))

        assert code == 0
        assert data["task"] == {"line": task["line"], "text": "작업", "done": False, "time": None}
        assert data["timeline_removed"] is True
        assert data["notices"] == []
        assert timeline_entries(base) == []
        assert "- [ ] 작업\n" in DailyPlan(base).get_plan_path().read_text(encoding="utf-8")
        assert data["plan"]["progress"] == {"done": 0, "total": 1}

    def test_undo_keeps_other_timeline_entries(self, base):
        runner.invoke(app, ["record", "다른 기록"])
        plan("daily", "add", "작업")
        plan("daily", "done", "1")

        plan_json("daily", "undo", "1")

        assert [e["text"] for e in timeline_entries(base)] == ["다른 기록"]

    def test_undo_without_the_entry_still_reopens_and_says_so(self, base):
        write_daily(base, TODAY, ["- [x] 손으로 체크한 일 [08:00]"])

        data, code = plan_json("daily", "undo", "1")

        assert code == 0
        assert data["task"]["done"] is False
        assert data["timeline_removed"] is False
        assert [n["kind"] for n in data["notices"]] == ["plan"]

    def test_undo_for_people(self, base):
        write_daily(base, TODAY, ["- [x] 끝낸 일 [08:00]"])
        result = plan("daily", "undo", "끝낸")
        assert result.exit_code == 0, result.output
        assert "- [ ] 끝낸 일" in result.output

    def test_undo_of_an_incomplete_task_is_not_found(self, base):
        write_daily(base, TODAY, ["- [ ] 남은 일"])
        data, code = plan_json("daily", "undo", "남은 일")
        assert (code, data["code"]) == (1, "not_found")


# ---------------------------------------------------------------------------
# 8. carryover --task
# ---------------------------------------------------------------------------


class TestCarryover:
    def test_named_tasks_without_asking(self, base):
        write_daily(base, YESTERDAY, ["- [ ] 가", "- [ ] 나", "- [ ] 다", "- [x] 끝낸 일 [09:00]"])
        write_daily(base, TODAY, ["- [ ] 나"])

        data, code = plan_json("daily", "carryover", "--task", "가", "--task", "나", "--task", "끝낸 일", "--task", "다")

        assert code == 0
        assert data["from"] == f"{YESTERDAY:%Y-%m-%d}"
        assert data["carried"] == ["가", "다"]
        assert data["skipped"] == ["나"]
        assert data["missing"] == ["끝낸 일"]
        assert [t["text"] for t in data["plan"]["tasks"]] == ["가", "다", "나"]

    def test_carryover_does_not_wait_for_input(self, base):
        write_daily(base, YESTERDAY, ["- [ ] 가"])
        result = runner.invoke(app, ["plan", "daily", "carryover", "--task", "가"], input="")
        assert result.exit_code == 0, result.output
        assert "Carried over 1 task(s)" in result.output

    def test_json_without_tasks_is_refused(self, base):
        data, code = plan_json("daily", "carryover")
        assert (code, data["code"]) == (1, "invalid_argument")
