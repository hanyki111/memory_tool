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


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def record(*args):
    result = runner.invoke(app, ["record", *args, "--json"])
    return result, last_json(result.output)


class TestRecord:
    def test_entry_path_and_tags(self, base):
        result, data = record("[버그] 로그인 오류 수정 #auth", "--time", "00:00")

        assert result.exit_code == 0
        assert data["ok"] is True
        assert data["entry"] == {
            "date": f"{datetime.now():%Y-%m-%d}", "time": "00:00",
            "text": "[버그] [auth] 로그인 오류 수정", "tags": ["버그", "auth"],
        }
        assert data["path"].endswith(".md")
        assert "로그인 오류 수정" in open(data["path"], encoding="utf-8").read()
        assert data["notices"] == []

    def test_future_time(self, base):
        tomorrow = datetime.now() + timedelta(days=1)

        result, data = record("x", "--date", f"{tomorrow:%Y-%m-%d}")

        assert result.exit_code == 1 and data["code"] == "future_time"

    def test_distant_past_can_be_forced(self, base):
        result, data = record("x", "--date", "2001-01-01")
        assert result.exit_code == 1 and data["code"] == "distant_past"
        assert "--force" in data["error"]

        result, data = record("x", "--date", "2001-01-01", "--force")
        assert data["ok"] is True and data["entry"]["date"] == "2001-01-01"

    def test_bad_time_is_invalid_argument(self, base):
        result, data = record("x", "--time", "25:99")

        assert result.exit_code == 1 and data["code"] == "invalid_argument"

    def test_review_notice_on_the_first_entry_of_the_day(self, base, monkeypatch):
        monkeypatch.setattr("memory_tool.review.notice.review_notice", lambda *a, **k: "리뷰할 때입니다")

        _, first = record("first", "--time", "00:00")
        _, second = record("second", "--time", "00:00")

        assert first["notices"] == [{"kind": "review", "message": "리뷰할 때입니다"}]
        assert second["notices"] == []

    def test_document_health_notice(self, base, monkeypatch):
        monkeypatch.setattr(
            "memory_tool.utils.suggestion_helper.document_health_notice", lambda *a, **k: "a.md is getting large"
        )

        _, data = record("x", "--time", "00:00")

        assert {"kind": "document_health", "message": "a.md is getting large"} in data["notices"]


class TestDocumentHealthNotice:
    class Issue:
        module_name, file_type, line_count = "work", "decisions", 900

    def test_warning_text(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "memory_tool.utils.suggestion_helper._pending_health_issues", lambda *a: ("warning", [self.Issue()])
        )
        from memory_tool.utils.suggestion_helper import document_health_notice

        assert document_health_notice(tmp_path, "m") == (
            "work/decisions.md is getting large (900 lines). Consider: marchive decisions --module work --suggest"
        )

    def test_nothing_to_say(self, tmp_path, monkeypatch):
        monkeypatch.setattr("memory_tool.utils.suggestion_helper._pending_health_issues", lambda *a: None)
        from memory_tool.utils.suggestion_helper import document_health_notice

        assert document_health_notice(tmp_path, "m") is None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search(*args):
    # --no-cache keeps the tests out of the user's global search cache.
    result = runner.invoke(app, ["search", *args, "--no-cache", "--no-index", "--json"])
    return result, last_json(result.output)


@pytest.fixture
def searchable(base):
    write_day(base, date(2026, 3, 1), "- 15:10 | 서버 포트를 8443으로 변경 #설정\n- 16:00 | 다른 일\n")
    (base / "modules" / "server.md").write_text("# Server\n\n포트 8443은 내부용입니다.\n", encoding="utf-8")
    return base


class FakeVectorSearcher:
    def __init__(self, *args, **kwargs):
        pass

    def semantic_search(self, query, top_k=10, threshold=0.5):
        path = FakeVectorSearcher.path
        # Semantic search keeps the entry text without its time.
        return [{"content": "서버 포트를 8443으로 변경 #설정", "date": "daily-2026-03", "file": str(path), "line": 2, "similarity": 0.9}]


class TestSearch:
    def test_keyword_results_with_entries(self, searchable):
        result, data = search("8443")

        assert result.exit_code == 0
        assert (data["ok"], data["query"], data["mode"], data["cached"]) == (True, "8443", "keyword", False)

        by_kind = {item["kind"]: item for item in data["results"]}
        timeline = by_kind["timeline"]
        assert timeline["date"] == "2026-03-01"
        assert timeline["entry"] == {"date": "2026-03-01", "time": "15:10", "text": "서버 포트를 8443으로 변경 #설정", "tags": ["설정"]}
        assert "entry" not in by_kind["module"]
        assert by_kind["module"]["path"].endswith("server.md")

    def test_no_results_is_an_empty_list(self, searchable):
        _, data = search("없는단어")

        assert data["ok"] is True and data["results"] == []

    def test_bad_period(self, searchable):
        result, data = search("8443", "--from", "2026-03-05", "--to", "2026-03-01")

        assert result.exit_code == 1 and data["code"] == "invalid_argument"

    def test_semantic_hit_gets_its_time_from_the_file(self, searchable, monkeypatch):
        FakeVectorSearcher.path = searchable / "timeline" / "daily" / "2026-03" / "2026-03-01.md"
        monkeypatch.setattr("memory_tool.core.vector_search.VectorSearcher", FakeVectorSearcher)

        _, data = search("포트", "--semantic")

        [item] = data["results"]
        assert data["mode"] == "semantic"
        assert item["score"] == 0.9 and item["date"] == "2026-03-01"
        assert item["entry"]["time"] == "15:10"

    def test_missing_vector_package(self, searchable, monkeypatch):
        from memory_tool.core import vector_search

        class Unavailable:
            def __init__(self, *args, **kwargs):
                raise vector_search.VectorSearchNotAvailableError("no model")

        monkeypatch.setattr("memory_tool.core.vector_search.VectorSearcher", Unavailable)

        result, data = search("포트", "--semantic")

        assert result.exit_code == 1 and data["code"] == "feature_unavailable"

    def test_hybrid(self, searchable, monkeypatch):
        FakeVectorSearcher.path = searchable / "timeline" / "daily" / "2026-03" / "2026-03-01.md"
        monkeypatch.setattr("memory_tool.core.vector_search.VectorSearcher", FakeVectorSearcher)

        result, data = search("8443", "--hybrid")

        assert result.exit_code == 0 and data["mode"] == "hybrid"
        assert any(item.get("entry", {}).get("time") == "15:10" for item in data["results"])


# ---------------------------------------------------------------------------
# AI commands
# ---------------------------------------------------------------------------


class FakeLLM:
    available = True
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def check_availability(cls, provider=None):
        return cls.available

    @classmethod
    def removed_provider_notice(cls, provider=None):
        return None

    def summarize(self, content, system_prompt=None, **kwargs):
        FakeLLM.calls += 1
        return "요약입니다."


@pytest.fixture
def llm(monkeypatch):
    FakeLLM.available = True
    FakeLLM.calls = 0
    for target in (
        "memory_tool.commands.planning.LLMClient",
        "memory_tool.commands.modules.LLMClient",
        "memory_tool.llm.client.LLMClient",
    ):
        monkeypatch.setattr(target, FakeLLM)
    return FakeLLM


def invoke_json(*args):
    result = runner.invoke(app, list(args))
    return result, last_json(result.output)


class TestSummary:
    def test_date_summary_then_cached(self, base, llm):
        write_day(base, date(2026, 3, 1), "- 10:00 | 합성 기록\n")

        result, first = invoke_json("summary", "2026-03-01", "--json")
        _, second = invoke_json("summary", "2026-03-01", "--json")

        assert result.exit_code == 0, result.output
        assert first == {
            "ok": True, "kind": "timeline", "scope": "2026-03-01",
            "summary": first["summary"], "cached": False, "saved_to": None,
        }
        assert "요약입니다." in first["summary"]
        assert second["cached"] is True and llm.calls == 1

    def test_missing_day_is_not_found(self, base, llm):
        result, data = invoke_json("summary", "2026-03-01", "--json")

        assert result.exit_code == 1 and data["code"] == "not_found"

    def test_bad_scope(self, base, llm):
        result, data = invoke_json("summary", "yesterday-ish", "--json")

        assert result.exit_code == 1 and data["code"] == "invalid_argument"

    def test_no_llm(self, base, llm):
        llm.available = False

        result, data = invoke_json("summary", "today", "--json")

        assert result.exit_code == 1 and data["code"] == "llm_unavailable"
        assert "mproviders" in data["error"]


class TestModuleAI:
    def test_suggest_links(self, base, llm, monkeypatch):
        (base / "modules" / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
        (base / "modules" / "beta.md").write_text("# Beta\n", encoding="utf-8")
        monkeypatch.setattr(
            "memory_tool.core.ai_suggester.AIConnectionSuggester.suggest_connections",
            lambda self, path, candidates, max_suggestions=10: [("beta", "같은 주제", 0.8)],
        )

        result, data = invoke_json("module", "suggest-links", "alpha", "--ai", "--json")

        assert result.exit_code == 0, result.output
        assert data["module"] == "alpha"
        assert data["suggestions"] == [{
            "module": "beta", "path": str((base / "modules" / "beta.md").resolve()),
            "reason": "같은 주제", "confidence": 0.8,
        }]

    def test_old_name_is_a_notice(self, base, llm, monkeypatch):
        (base / "modules" / "alpha.md").write_text("# Alpha\n", encoding="utf-8")
        monkeypatch.setattr(
            "memory_tool.core.ai_suggester.AIConnectionSuggester.suggest_connections",
            lambda self, path, candidates, max_suggestions=10: [],
        )

        _, data = invoke_json("module", "suggest-ai", "alpha", "--json")

        assert data["ok"] is True and data["notices"][0]["kind"] == "renamed"

    def test_unknown_module(self, base, llm):
        result, data = invoke_json("module", "suggest-links", "nothing", "--ai", "--json")

        assert result.exit_code == 1 and data["code"] == "not_found"

    def test_from_text(self, base, llm, monkeypatch):
        from memory_tool.core.ai_module_generator import GeneratedModule

        monkeypatch.setattr(
            "memory_tool.core.ai_module_generator.AIModuleGenerator.generate",
            lambda self, text, language="auto": GeneratedModule(
                name="backup-notes", doc_type="참고", description="백업 설정", body="# 백업\n\n본문\n",
            ),
        )

        _, preview = invoke_json("module", "from-text", "--text", "합성 글", "--preview", "--json")
        assert preview["saved"] is False and preview["document"]["body"].startswith("# 백업")
        assert not list((base / "modules").rglob("backup-notes*"))

        result, saved = invoke_json("module", "from-text", "--text", "합성 글", "--json")
        assert result.exit_code == 0, result.output
        assert saved["saved"] is True and saved["document"]["name"] == "backup-notes"
        assert "body" not in saved["document"]
        assert open(saved["path"], encoding="utf-8").read()

    def test_json_with_other_actions(self, base):
        result, data = invoke_json("module", "list", "--json")

        assert result.exit_code == 1 and data["code"] == "invalid_argument"


class TestExistingJson:
    def test_review_without_a_knowledge_base(self, base, monkeypatch):
        monkeypatch.setattr("memory_tool.commands.review.get_base_path", lambda: base.parent / "missing")

        result, data = invoke_json("review", "--json")

        assert result.exit_code == 1 and data["code"] == "not_initialized"

    def test_review_llm_failure(self, base, monkeypatch):
        class Broken:
            def __init__(self, *args, **kwargs):
                pass

            def generate(self, prompt, system_prompt=None, **kwargs):
                return "not json"

        monkeypatch.setattr("memory_tool.llm.client.LLMClient", Broken)
        write_day(base, datetime.now(), "- 00:00 | 합성 기록\n")

        result, data = invoke_json("review", "--json")

        assert result.exit_code == 1 and data["code"] == "llm_failed"

    def test_mask_keeps_its_fields_and_adds_a_code(self, base, monkeypatch):
        def unavailable(**kwargs):
            raise RuntimeError("No provider")

        monkeypatch.setattr("memory_tool.commands.qa._ask_agent", unavailable)

        result, data = invoke_json("ask", "질문", "--json")

        assert result.exit_code == 1
        assert data["code"] == "llm_unavailable"
        assert {"ok", "question", "error", "available_providers"} <= set(data)
