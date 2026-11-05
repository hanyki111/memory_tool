"""Regression tests for the AI features, on synthetic data only.

No AI code was covered by a test, so renaming timeline files and consolidating
modules broke mask and msummary without anything failing. An LLM is replaced by
a fake: these tests are about which records reach it, not about its answers.
"""

from datetime import date

import pytest

from memory_tool.core.doc_sections import SectionError, read_decisions_text
from memory_tool.core.memory_agent import MemoryAgent, ToolCall
from memory_tool.core.timeline import Timeline
from memory_tool.llm.claude_cli_client import ClaudeCLIClient
from memory_tool.summary.module_summarizer import ModuleSummarizer
from memory_tool.summary.timeline_summarizer import TimelineSummarizer
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    base = tmp_path / ".memory"
    (base / "modules").mkdir(parents=True)
    (base / "timeline" / "daily").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield tmp_path
    clear_cache()


@pytest.fixture
def base(project):
    return project / ".memory"


@pytest.fixture
def agent(project):
    return MemoryAgent(project)


class FakeLLM:
    """Stands in for LLMClient and records what it was asked."""

    def __init__(self, responses=()):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt, system_prompt=None, **kwargs):
        self.prompts.append(prompt)
        return self.responses.pop(0)

    def summarize(self, content, system_prompt=None, **kwargs):
        self.prompts.append(content)
        return "SUMMARY"


def write_timeline(base, relative, text):
    path = base / "timeline" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- timeline tools ----------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "daily/2026-09/2026-09-03.md",
        "daily/2026-09/03.md",
        "2026-09/03.md",
    ],
)
def test_get_timeline_reads_every_file_layout(agent, base, relative):
    write_timeline(base, relative, "# day\n- 10:00 | synthetic entry\n")

    assert "synthetic entry" in agent._tool_get_timeline("2026-09-03")


def test_get_timeline_says_so_when_the_day_has_no_file(agent):
    assert "No timeline found for 2026-09-03" in agent._tool_get_timeline("2026-09-03")


def test_an_unreadable_date_fails_instead_of_answering_with_today(agent, base):
    today = date.today()
    write_timeline(
        base,
        f"daily/{today:%Y-%m}/{today:%Y-%m-%d}.md",
        "- 10:00 | entry from today\n",
    )

    result = agent._execute_tool(ToolCall(tool="get_timeline", args={"date": "last spring"}))

    assert result.success is False
    assert "last spring" in result.error


@pytest.mark.parametrize("written", ["2026-9-3", "2026/09/03", "2026.09.03"])
def test_common_date_spellings_are_understood(agent, written):
    assert agent._parse_date(written) == date(2026, 9, 3)


def test_range_finds_both_file_names(agent, base):
    today = date.today()
    write_timeline(base, f"daily/{today:%Y-%m}/{today:%Y-%m-%d}.md", "- 10:00 | new name\n")
    write_timeline(base, f"daily/{today:%Y-%m}/{today:%d}.md", "- 10:00 | ignored duplicate\n")

    assert "new name" in agent._tool_get_timeline_range(1)


def test_range_between_explicit_dates(agent, base):
    write_timeline(base, "daily/2026-09/2026-09-02.md", "- 10:00 | before\n")
    write_timeline(base, "daily/2026-09/2026-09-03.md", "- 10:00 | first\n")
    write_timeline(base, "daily/2026-09/04.md", "- 10:00 | second\n")
    write_timeline(base, "daily/2026-09/2026-09-05.md", "- 10:00 | after\n")

    result = agent._tool_get_timeline_range(start="2026-09-03", end="2026-09-04")

    assert "first" in result and "second" in result
    assert "before" not in result and "after" not in result


def test_range_does_not_report_nothing_when_a_file_has_entries_in_another_form(agent, base):
    write_timeline(
        base,
        "daily/2026-09/2026-09-03.md",
        "# 2026-09-03 Timeline\nwritten by hand without a bullet\n",
    )

    result = agent._tool_get_timeline_range(start="2026-09-03", end="2026-09-03")

    assert "written by hand" in result
    assert "No timeline entries" not in result


def test_range_reports_the_period_it_searched(agent):
    result = agent._tool_get_timeline_range(start="2026-09-03", end="2026-09-04")

    assert "No timeline entries" in result
    assert "2026-09-03" in result and "2026-09-04" in result


def test_range_accepts_days_as_text_from_the_llm(agent, base):
    today = date.today()
    write_timeline(base, f"daily/{today:%Y-%m}/{today:%Y-%m-%d}.md", "- 10:00 | entry\n")

    result = agent._execute_tool(ToolCall(tool="get_timeline_range", args={"days": "2"}))

    assert result.success is True
    assert "entry" in result.result


def test_a_question_about_a_date_reaches_that_days_records(agent, base, monkeypatch):
    write_timeline(base, "daily/2026-09/2026-09-03.md", "- 10:00 | the answer is here\n")
    llm = FakeLLM(
        [
            '{"reasoning": "date", "tool_calls": '
            '[{"tool": "get_timeline", "args": {"date": "2026-09-03"}}]}',
            "ANSWER",
        ]
    )

    import memory_tool.llm.client as client

    monkeypatch.setattr(client.LLMClient, "check_availability", staticmethod(lambda provider=None: True))
    monkeypatch.setattr(client.LLMClient, "get_provider", staticmethod(lambda: "fake"))
    monkeypatch.setattr(client, "LLMClient", _replacing(client.LLMClient, llm))

    result = agent.ask("2026-09-03에 무엇을 기록했지?")

    assert result.answer == "ANSWER"
    assert [call.tool for call in result.tool_calls] == ["get_timeline"]
    assert "the answer is here" in llm.prompts[1]


def _replacing(client_class, fake):
    class Replacement:
        check_availability = client_class.check_availability
        get_provider = client_class.get_provider
        list_available_providers = staticmethod(lambda: ["fake"])

        def __new__(cls, *args, **kwargs):
            return fake

    return Replacement


def test_tool_selection_prompt_names_specific_dates_and_periods(agent):
    prompt = agent._build_tool_selection_prompt("question")

    assert 'get_timeline(date="YYYY-MM-DD")' in prompt
    assert 'get_timeline_range(start="YYYY-MM-DD", end="YYYY-MM-DD")' in prompt


# --- module tools ------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    ["topic/topic.md", "topic.md", "topic/current.md"],
)
def test_get_module_reads_every_layout(agent, base, relative):
    path = base / "modules" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic body\n", encoding="utf-8")

    assert "synthetic body" in agent._tool_get_module("topic")


def test_list_modules_includes_single_documents_and_skips_plan_md(agent, base):
    for relative in ("single/single.md", "flat.md", "single/PLAN.md", "legacy/current.md"):
        path = base / "modules" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    result = agent._tool_list_modules()

    assert "- single" in result and "- flat" in result and "- legacy" in result
    assert "PLAN" not in result


def test_get_module_reports_a_missing_module(agent):
    assert "Module not found: missing" in agent._tool_get_module("missing")


# --- msummary ----------------------------------------------------------------


def summarizer():
    return TimelineSummarizer(FakeLLM())


@pytest.mark.parametrize(
    "relative",
    ["daily/2026-09/2026-09-03.md", "daily/2026-09/03.md", "2026-09/03.md"],
)
def test_summarize_date_reads_every_layout(base, relative):
    write_timeline(base, relative, "- 10:00 | synthetic entry\n")
    subject = summarizer()

    assert subject.summarize_date(date(2026, 9, 3), force=True) == "SUMMARY"
    assert "synthetic entry" in subject.llm_client.prompts[0]


def test_summarize_date_without_a_file_raises_and_creates_nothing(base):
    with pytest.raises(FileNotFoundError):
        summarizer().summarize_date(date(2026, 9, 3))

    assert not (base / "timeline" / "daily" / "2026-09").exists()


def test_summarize_week_saves_its_result(base):
    write_timeline(base, "daily/2026-08/2026-08-31.md", "- 10:00 | monday\n")
    write_timeline(base, "daily/2026-09/03.md", "- 10:00 | thursday\n")
    subject = summarizer()

    assert subject.summarize_week(date(2026, 8, 31), force=True) == "SUMMARY"

    assert "monday" in subject.llm_client.prompts[0]
    assert "thursday" in subject.llm_client.prompts[0]
    assert list((base / "summaries").rglob("*W36*"))


def test_summarize_week_serves_the_saved_summary_until_a_file_changes(base):
    path = write_timeline(base, "daily/2026-08/2026-08-31.md", "- 10:00 | monday\n")
    subject = summarizer()

    subject.summarize_week(date(2026, 8, 31))
    subject.summarize_week(date(2026, 8, 31))
    assert len(subject.llm_client.prompts) == 1

    path.write_text("- 10:00 | monday\n- 11:00 | more\n", encoding="utf-8")
    subject.summarize_week(date(2026, 8, 31))
    assert len(subject.llm_client.prompts) == 2


def test_summarize_range_reads_both_names(base):
    write_timeline(base, "daily/2026-09/2026-09-03.md", "- 10:00 | first\n")
    write_timeline(base, "daily/2026-09/04.md", "- 10:00 | second\n")
    subject = summarizer()

    assert subject.summarize_range(date(2026, 9, 3), date(2026, 9, 4), force=True) == "SUMMARY"
    assert "first" in subject.llm_client.prompts[0]
    assert "second" in subject.llm_client.prompts[0]


@pytest.mark.parametrize("relative", ["topic/topic.md", "topic.md", "topic/current.md"])
def test_summarize_module_reads_every_layout(base, relative):
    path = base / "modules" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic module body\n", encoding="utf-8")
    llm = FakeLLM()

    summary = ModuleSummarizer(llm).summarize_module(base / "modules" / "topic", force=True)

    assert summary == "SUMMARY"
    assert "synthetic module body" in llm.prompts[0]


def test_summarize_module_reports_a_missing_module(base):
    with pytest.raises(FileNotFoundError):
        ModuleSummarizer(FakeLLM()).summarize_module(base / "modules" / "missing")


def test_summarize_all_modules_covers_flat_and_nested_documents(base):
    for relative in ("flat.md", "group/child.md", "group/PLAN.md"):
        path = base / "modules" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic\n", encoding="utf-8")

    summaries = ModuleSummarizer(FakeLLM()).summarize_all_modules(base / "modules", force=True)

    assert set(summaries) == {"flat", "group/child"}


# --- decisions ---------------------------------------------------------------


def test_decisions_come_from_the_legacy_file(base):
    path = base / "modules" / "topic" / "decisions.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Decisions\n\nlegacy entry\n", encoding="utf-8")

    assert "legacy entry" in read_decisions_text(base / "modules" / "topic")


def test_decisions_come_from_the_section_of_a_single_document(base):
    path = base / "modules" / "topic.md"
    path.write_text(
        "# Topic\n\nbody\n\n# Decisions\n\nsection entry\n\n# Scope\n\nother\n",
        encoding="utf-8",
    )

    text = read_decisions_text(base / "modules" / "topic")

    assert "section entry" in text
    assert "body" not in text and "other" not in text


def test_a_document_without_decisions_returns_nothing(base):
    (base / "modules" / "topic.md").write_text("# Topic\n\nbody\n", encoding="utf-8")

    assert read_decisions_text(base / "modules" / "topic") is None
    assert read_decisions_text(base / "modules" / "missing") is None


def test_several_decision_sections_are_reported_rather_than_guessed(base):
    (base / "modules" / "topic.md").write_text(
        "# Decisions\n\none\n\n# Decisions\n\ntwo\n", encoding="utf-8"
    )

    with pytest.raises(SectionError):
        read_decisions_text(base / "modules" / "topic")


# --- claude-cli --------------------------------------------------------------


def test_claude_cli_sends_the_prompt_on_stdin(monkeypatch):
    """A long prompt must not depend on the Windows command-line length limit."""
    import memory_tool.llm.cli_client as module

    seen = {}

    class Completed:
        returncode = 0
        stdout = "reply"
        stderr = ""

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["input"] = kwargs.get("input")
        return Completed()

    monkeypatch.setattr(module.shutil, "which", lambda command: command)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    long_prompt = "synthetic " * 20000

    assert ClaudeCLIClient(command="claude")._call_cli(long_prompt, "system") == "reply"

    assert long_prompt not in " ".join(seen["cmd"])
    assert long_prompt in seen["input"]
    assert "system" in seen["input"]


def test_timeline_helper_stays_read_only(base):
    assert Timeline.resolve_existing_file(base / "timeline", date(2026, 9, 3)) is None
    assert list((base / "timeline" / "daily").iterdir()) == []
