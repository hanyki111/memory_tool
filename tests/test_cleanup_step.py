"""Tests for removed commands, provider selection and the no-LLM message."""

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app, console, print_llm_unavailable
from memory_tool.context.builder import ContextBuilder
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
    (base / "plans").mkdir()
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield tmp_path
    clear_cache()


def set_available(monkeypatch, *available):
    monkeypatch.setattr(
        LLMClient,
        "check_availability",
        classmethod(lambda cls, provider=None: provider in available),
    )


def set_configured(project, provider):
    config = project / ".memory" / "config.yaml"
    config.write_text(f"version: '1.0'\nllm:\n  provider: {provider}\n", encoding="utf-8")
    clear_cache()


# --- provider ----------------------------------------------------------------


def test_only_a_cli_being_installed_is_enough(monkeypatch):
    set_available(monkeypatch, "claude-cli")

    assert LLMClient.get_provider() == "claude-cli"


def test_an_api_key_is_preferred_over_a_cli(monkeypatch):
    set_available(monkeypatch, "claude-cli", "anthropic")

    assert LLMClient.get_provider() == "anthropic"


def test_nothing_available_still_names_a_provider(monkeypatch):
    set_available(monkeypatch)

    assert LLMClient.get_provider() == "anthropic"


def test_a_configured_provider_is_not_replaced_when_unavailable(project, monkeypatch):
    set_configured(project, "ollama")
    set_available(monkeypatch, "claude-cli")

    assert LLMClient.get_provider() == "ollama"


def test_available_providers_are_listed_in_preference_order(monkeypatch):
    set_available(monkeypatch, "ollama", "claude-cli")

    assert LLMClient.list_available_providers() == ["claude-cli", "ollama"]


# --- messages ----------------------------------------------------------------


def test_no_llm_message_names_more_than_an_api_key(capsys):
    print_llm_unavailable(console)

    output = " ".join(capsys.readouterr().out.split())
    for expected in ("claude", "Ollama", "ANTHROPIC_API_KEY", "llm.provider", "mproviders"):
        assert expected in output


# --- removed commands --------------------------------------------------------


def test_auto_tag_is_gone():
    result = runner.invoke(app, ["module", "auto-tag", "topic"])

    assert result.exit_code != 0
    assert "Unknown action" in result.output
    assert "auto-tag" not in result.output.replace("Unknown action: auto-tag", "")


def test_mplan_module_is_gone(project):
    result = runner.invoke(app, ["plan", "module", "topic"])

    assert result.exit_code != 0
    assert not list((project / ".memory").rglob("PLAN.md"))


@pytest.mark.parametrize("argument", [["plan", "--help"]])
def test_plan_help_no_longer_offers_module(argument):
    result = runner.invoke(app, argument)

    assert result.exit_code == 0
    assert "--section" not in result.output
    assert "mplan module" not in result.output


def test_the_rest_of_mplan_still_works(project):
    created = runner.invoke(app, ["plan", "create", "Sample"])
    assert created.exit_code == 0, created.output

    listed = runner.invoke(app, ["plan", "list"])
    assert listed.exit_code == 0
    assert "Sample" in listed.output

    daily = runner.invoke(app, ["plan", "daily", "add", "synthetic task"])
    assert daily.exit_code == 0, daily.output
    assert any("synthetic task" in p.read_text(encoding="utf-8") for p in (project / ".memory" / "plans").rglob("*.md"))


# --- mcontext ----------------------------------------------------------------


def test_context_has_no_stale_module_guidance(project):
    content = ContextBuilder(project).build_context_content()

    assert "Module Organization Quick Reference" not in content
    assert "current.md` > 300" not in content


def test_context_quick_action_names_a_real_archive_target(project):
    document = project / ".memory" / "modules" / "topic.md"
    document.write_text("line\n" * 1500, encoding="utf-8")

    content = ContextBuilder(project).build_context_content()

    assert "marchive decisions --module topic --interactive" in content
    assert "marchive topic" not in content
