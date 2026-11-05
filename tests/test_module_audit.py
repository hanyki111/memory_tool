"""Tests for mmodule audit and suggest-links --ai, formerly ai-organize and suggest-ai."""

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.core.ai_suggester import AIConnectionSuggester
from memory_tool.core.module_audit import (
    AuditReport,
    ModuleAnalyzer,
    ModuleAuditor,
    SuggestionType,
    count_sections,
    format_report,
)
from memory_tool.llm.client import LLMClient
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    base = tmp_path / ".memory"
    (base / "modules").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield tmp_path
    clear_cache()


@pytest.fixture
def modules(project):
    return project / ".memory" / "modules"


@pytest.fixture
def no_embeddings(monkeypatch):
    monkeypatch.setattr(ModuleAnalyzer, "can_measure_similarity", lambda self: False)


def write(modules, relative, text="# doc\n"):
    path = modules / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def long_document(sections=6, lines_per_section=60):
    return "".join(
        f"## Section {i}\n" + "line\n" * lines_per_section for i in range(sections)
    )


def test_measures_every_layout(modules):
    write(modules, "folder/folder.md", long_document())
    write(modules, "flat.md", "line\n" * 10)
    write(modules, "legacy/current.md", "line\n" * 5)
    write(modules, "legacy/decisions.md", "line\n" * 7)
    write(modules, "folder/PLAN.md", "line\n" * 1000)

    found = {m.name: m for m in ModuleAnalyzer(modules).discover_all_modules()}

    assert set(found) == {"flat", "folder", "legacy"}
    assert found["folder"].line_count == 366
    assert found["flat"].line_count == 10
    assert found["legacy"].line_count == 12


def test_a_large_single_document_is_not_reported_as_fine(modules, no_embeddings):
    write(modules, "large/large.md", long_document())

    report = ModuleAuditor(modules).audit()

    assert [(s.type, s.module_name) for s in report.suggestions] == [
        (SuggestionType.SPLIT, "large")
    ]


def test_a_long_lookup_table_is_not_a_split_candidate(modules, no_embeddings):
    write(modules, "table.md", "# Table\n\n" + "| a | b |\n" * 1000)

    assert ModuleAuditor(modules).audit().suggestions == []


def test_split_candidates_are_ordered_longest_first(modules, no_embeddings):
    write(modules, "shorter.md", long_document(lines_per_section=60))
    write(modules, "longer.md", long_document(lines_per_section=90))

    names = [s.module_name for s in ModuleAuditor(modules).audit().suggestions]

    assert names == ["longer", "shorter"]


def test_top_level_modules_are_not_treated_as_a_problem(modules, no_embeddings):
    write(modules, "topic.md", "# Topic\n\nbody\n")

    assert ModuleAuditor(modules).audit().suggestions == []


def test_scope_matches_whole_path_parts(modules, no_embeddings):
    write(modules, "topic/child.md", long_document())
    write(modules, "topic2.md", long_document())

    report = ModuleAuditor(modules).audit(scope="topic")

    assert report.modules_examined == 1
    assert [s.module_name for s in report.suggestions] == ["topic/child"]


def test_merge_candidates_must_both_be_small(modules, monkeypatch):
    write(modules, "small_a.md", "text\n")
    write(modules, "small_b.md", "text\n")
    write(modules, "big.md", "text\n" * 500)
    monkeypatch.setattr(ModuleAnalyzer, "can_measure_similarity", lambda self: True)

    def similar(self, infos, threshold=0.65):
        by_name = {info.name: info for info in infos}
        return [
            (by_name["small_a"], by_name["small_b"], 0.9),
            (by_name["small_a"], by_name["big"], 0.9),
        ]

    monkeypatch.setattr(ModuleAnalyzer, "find_similar_modules", similar)

    report = ModuleAuditor(modules).audit()
    merges = [s for s in report.suggestions if s.type == SuggestionType.MERGE]

    assert [(m.module_name, m.details["other_module"]) for m in merges] == [("small_a", "small_b")]


def test_an_unmeasured_merge_is_reported_rather_than_implied_clean(modules, no_embeddings):
    report = ModuleAuditor(modules).audit()

    assert report.merges_checked is False
    assert "not checked" in format_report(report)


def test_report_says_nothing_was_changed():
    output = format_report(AuditReport([], modules_examined=3, merges_checked=True))

    assert "No candidates found" in output
    assert "Nothing was changed" in output


def test_report_limit_mentions_what_it_hid(modules, no_embeddings):
    for name in ("a", "b", "c"):
        write(modules, f"{name}.md", long_document())

    output = format_report(ModuleAuditor(modules).audit(), limit=1)

    assert "and 2 more" in output


def test_headings_inside_code_fences_do_not_count():
    assert count_sections("# real\n```\n# comment\n## also\n```\n## real\n") == 2


def test_audit_changes_no_files(modules, no_embeddings):
    document = write(modules, "large.md", long_document())
    before = document.read_bytes()

    ModuleAuditor(modules).audit()

    assert document.read_bytes() == before
    assert sorted(p.name for p in modules.rglob("*")) == ["large.md"]


# --- commands ----------------------------------------------------------------


def test_audit_command(modules, no_embeddings):
    write(modules, "large.md", long_document())

    result = runner.invoke(app, ["module", "audit"])

    assert result.exit_code == 0, result.output
    assert "large" in result.output
    assert "Split candidates" in result.output


def test_old_name_still_works_and_warns(modules, no_embeddings):
    write(modules, "large.md", long_document())

    result = runner.invoke(app, ["module", "ai-organize"])

    assert result.exit_code == 0, result.output
    assert "audit" in result.output
    assert "large" in result.output


@pytest.fixture
def llm_available(monkeypatch):
    monkeypatch.setattr(
        LLMClient, "check_availability", classmethod(lambda cls, provider=None: True)
    )
    monkeypatch.setattr(AIConnectionSuggester, "__init__", lambda self, *a, **k: None)
    calls = {}

    def suggest(self, module_path, candidates, max_suggestions=5, skip_cache=False):
        calls["module_path"] = module_path
        calls["candidates"] = [name for name, _ in candidates]
        calls["max"] = max_suggestions
        return [("other", "synthetic reason", 0.9)]

    monkeypatch.setattr(AIConnectionSuggester, "suggest_connections", suggest)
    return calls


def test_suggest_links_ai_accepts_a_flat_module(modules, llm_available):
    write(modules, "topic.md")
    write(modules, "group/other.md")

    result = runner.invoke(app, ["module", "suggest-links", "topic", "--ai", "--limit", "3"])

    assert result.exit_code == 0, result.output
    assert "synthetic reason" in result.output
    assert llm_available["candidates"] == ["group/other"]
    assert llm_available["max"] == 3


def test_suggest_ai_old_name_still_works_and_warns(modules, llm_available):
    write(modules, "topic.md")

    result = runner.invoke(app, ["module", "suggest-ai", "topic"])

    assert result.exit_code == 0, result.output
    assert "suggest-links" in result.output
    assert "synthetic reason" in result.output


def test_suggest_links_ai_reports_a_missing_module(modules, llm_available):
    result = runner.invoke(app, ["module", "suggest-links", "missing", "--ai"])

    assert result.exit_code != 0
    assert "Module not found" in result.output


def test_suggest_links_without_ai_needs_no_llm(modules, monkeypatch):
    write(modules, "group/topic.md")
    write(modules, "group/other.md")
    monkeypatch.setattr(
        LLMClient, "check_availability", classmethod(lambda cls, provider=None: False)
    )

    result = runner.invoke(app, ["module", "suggest-links", "group/topic"])

    assert result.exit_code == 0, result.output
    assert "group/other" in result.output


def test_suggester_reads_the_body_of_a_single_document(modules):
    write(modules, "topic.md", "synthetic body")
    suggester = AIConnectionSuggester.__new__(AIConnectionSuggester)

    assert suggester._read_module_content(modules / "topic") == "synthetic body"


def test_suggester_leaves_decision_logs_out_of_a_legacy_module(modules):
    write(modules, "topic/current.md", "state")
    write(modules, "topic/decisions.md", "decision log")
    suggester = AIConnectionSuggester.__new__(AIConnectionSuggester)

    content = suggester._read_module_content(modules / "topic")

    assert "state" in content
    assert "decision log" not in content
