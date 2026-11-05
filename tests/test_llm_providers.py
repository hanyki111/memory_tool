"""Tests for the CLI-based LLM providers, with the processes replaced by fakes."""

import json
import os
from pathlib import Path

import pytest

import memory_tool.llm.cli_client as cli_module
from memory_tool.commands.common import console, print_llm_unavailable
from memory_tool.core.memory_agent import MemoryAgent
from memory_tool.llm.antigravity_cli_client import AntigravityCLIClient
from memory_tool.llm.claude_cli_client import ClaudeCLIClient
from memory_tool.llm.client import LLMClient
from memory_tool.llm.codex_cli_client import CodexCLIClient
from memory_tool.llm.glm_client import GLMClient, load_connection, read_ps1_environment
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

FAKE_TOKEN = "synthetic-token-value"
FAKE_URL = "https://glm.example.test/anthropic"


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    base = tmp_path / ".memory"
    (base / "modules").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield tmp_path
    clear_cache()


def configure(project, text):
    (project / ".memory" / "config.yaml").write_text(f"version: '1.0'\n{text}", encoding="utf-8")
    clear_cache()


def ps1_file(project):
    path = project / "set-glm.ps1"
    path.write_text(
        f"$env:ANTHROPIC_AUTH_TOKEN = '{FAKE_TOKEN}'\n"
        f'$env:ANTHROPIC_BASE_URL = "{FAKE_URL}"\n'
        "$env:ANTHROPIC_DEFAULT_OPUS_MODEL = glm-example  # comment\n"
        "$env:UNRELATED_SECRET = 'must-not-be-read'\n"
        "# $env:ANTHROPIC_MODEL = 'commented-out'\n",
        encoding="utf-8-sig",
    )
    return path


@pytest.fixture
def glm_configured(project):
    configure(project, f"llm:\n  glm:\n    env_from_ps1: {ps1_file(project).as_posix()}\n")


class Completed:
    def __init__(self, stdout="answer", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


@pytest.fixture
def process(monkeypatch):
    """Replace subprocess.run; set ``process.result`` to change what it returns."""

    class Recorder:
        result = Completed()
        calls = []

    Recorder.calls = []

    def fake_run(command, **kwargs):
        Recorder.calls.append({"command": command, **kwargs})
        return Recorder.result

    monkeypatch.setattr(cli_module.shutil, "which", lambda name: f"C:/bin/{name}.cmd")
    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)
    return Recorder


ALL_CLI_CLIENTS = [ClaudeCLIClient, CodexCLIClient, AntigravityCLIClient]


def antigravity_output(response="answer", status="SUCCESS", error=None):
    result = {"status": status, "response": response}
    if error:
        result["error"] = error
    return "\n".join(
        [
            json.dumps({"event": "init", "tools": ["write_to_file"]}),
            "not json at all",
            json.dumps({"event": "result", "result": result}),
        ]
    )


# --- what every CLI shares ---------------------------------------------------


@pytest.mark.parametrize("client_class", ALL_CLI_CLIENTS)
def test_a_long_prompt_never_goes_on_the_command_line(process, client_class):
    process.result = Completed(antigravity_output())
    long_prompt = "synthetic " * 20000

    client_class(command="tool").generate(long_prompt, "instructions")

    call = process.calls[0]
    assert long_prompt not in " ".join(call["command"])
    assert long_prompt[:1000] in call["input"]
    assert "instructions" in call["input"]


@pytest.mark.parametrize("client_class", ALL_CLI_CLIENTS)
def test_the_cli_runs_in_an_empty_folder_outside_the_project(process, project, client_class):
    process.result = Completed(antigravity_output())

    client_class(command="tool").generate("question")

    folder = Path(process.calls[0]["cwd"])
    assert project not in folder.parents and folder != project
    assert not folder.exists()  # Removed afterwards.


@pytest.mark.parametrize("client_class", ALL_CLI_CLIENTS)
def test_the_executable_is_resolved_for_windows_shims(process, client_class):
    process.result = Completed(antigravity_output())

    client_class(command="tool").generate("question")

    assert process.calls[0]["command"][0] == "C:/bin/tool.cmd"


@pytest.mark.parametrize("client_class", ALL_CLI_CLIENTS)
def test_output_is_decoded_as_utf8(process, client_class):
    process.result = Completed(antigravity_output())

    client_class(command="tool").generate("질문")

    assert process.calls[0]["encoding"] == "utf-8"
    assert process.calls[0]["errors"] == "replace"


@pytest.mark.parametrize("client_class", [ClaudeCLIClient, CodexCLIClient])
def test_a_failure_reports_the_error(process, client_class):
    process.result = Completed("", returncode=1, stderr="not logged in")

    with pytest.raises(RuntimeError, match="not logged in"):
        client_class(command="tool").generate("question")


@pytest.mark.parametrize("client_class", [ClaudeCLIClient, CodexCLIClient])
def test_an_empty_answer_is_an_error(process, client_class):
    process.result = Completed("   ")

    with pytest.raises(RuntimeError, match="Empty response"):
        client_class(command="tool").generate("question")


def test_a_timeout_is_reported(monkeypatch):
    def times_out(command, **kwargs):
        raise cli_module.subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(cli_module.shutil, "which", lambda name: name)
    monkeypatch.setattr(cli_module.subprocess, "run", times_out)

    with pytest.raises(RuntimeError, match="timed out"):
        CodexCLIClient(command="tool").generate("question")


def test_a_missing_cli_says_how_to_get_it(monkeypatch):
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="@openai/codex"):
        CodexCLIClient()


def test_summarize_passes_the_system_prompt(process):
    assert CodexCLIClient(command="tool").summarize("content", "instructions") == "answer"
    assert "instructions" in process.calls[0]["input"]


# --- Codex -------------------------------------------------------------------


def test_codex_runs_read_only_and_reads_stdin(process):
    CodexCLIClient(command="codex").generate("question")

    command = process.calls[0]["command"]
    assert command[1] == "exec"
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--skip-git-repo-check" in command
    assert "--ephemeral" in command
    assert command[-1] == "-"
    assert process.calls[0]["input"] == "question"


def test_codex_model_and_command_come_from_the_config(project, process):
    configure(project, "llm:\n  codex_cli:\n    command: my-codex\n    model: example-model\n")

    CodexCLIClient().generate("question")

    command = process.calls[0]["command"]
    assert command[0] == "C:/bin/my-codex.cmd"
    assert command[command.index("--model") + 1] == "example-model"
    assert command[-1] == "-"


# --- Antigravity -------------------------------------------------------------


def test_antigravity_runs_in_plan_mode_and_sends_a_stream_message(process):
    process.result = Completed(antigravity_output("the answer"))

    assert AntigravityCLIClient(command="agy").generate("질문") == "the answer"

    command = process.calls[0]["command"]
    assert command[command.index("--mode") + 1] == "plan"
    assert "--input-format=stream-json" in command
    assert "--output-format=stream-json" in command
    assert command[-1] == "--print="

    message = json.loads(process.calls[0]["input"])
    assert message["event"] == "user"
    assert message["message"]["role"] == "user"
    assert message["message"]["content"].endswith("질문")
    assert "Do not use any tools" in message["message"]["content"]


def test_antigravity_model_comes_before_the_print_flag(project, process):
    process.result = Completed(antigravity_output())
    configure(project, "llm:\n  antigravity_cli:\n    model: example-model\n")

    AntigravityCLIClient().generate("question")

    command = process.calls[0]["command"]
    assert command[command.index("--model") + 1] == "example-model"
    assert command[-1] == "--print="


def test_antigravity_reports_a_failed_result(process):
    process.result = Completed(antigravity_output("", status="ERROR", error="quota used up"))

    with pytest.raises(RuntimeError, match="quota used up"):
        AntigravityCLIClient(command="agy").generate("question")


def test_antigravity_says_when_a_denied_tool_left_no_answer(process):
    denied = {
        "event": "result",
        "result": {
            "status": "SUCCESS",
            "response": "",
            "denied_actions": [{"action": "command", "display_name": "RunCommand"}],
        },
    }
    process.result = Completed(json.dumps(denied))

    with pytest.raises(RuntimeError, match="RunCommand"):
        AntigravityCLIClient(command="agy").generate("question")


def test_antigravity_without_a_result_is_an_error(process):
    process.result = Completed(json.dumps({"event": "init"}))

    with pytest.raises(RuntimeError, match="no result"):
        AntigravityCLIClient(command="agy").generate("question")


# --- GLM ---------------------------------------------------------------------


def test_ps1_reading_keeps_only_connection_variables(project):
    values = read_ps1_environment(ps1_file(project))

    assert values == {
        "ANTHROPIC_AUTH_TOKEN": FAKE_TOKEN,
        "ANTHROPIC_BASE_URL": FAKE_URL,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-example",
    }


def test_connection_from_environment_variables(monkeypatch):
    monkeypatch.setenv("MY_GLM_KEY", FAKE_TOKEN)
    monkeypatch.setenv("MY_GLM_URL", FAKE_URL)

    values = load_connection(
        {"env_from_env": {"ANTHROPIC_AUTH_TOKEN": "MY_GLM_KEY", "ANTHROPIC_BASE_URL": "MY_GLM_URL"}}
    )

    assert values == {"ANTHROPIC_AUTH_TOKEN": FAKE_TOKEN, "ANTHROPIC_BASE_URL": FAKE_URL}


@pytest.mark.parametrize("settings", [None, {}, {"env_from_env": {"ANTHROPIC_BASE_URL": "ABSENT_VAR"}}])
def test_an_incomplete_connection_names_the_settings(settings):
    with pytest.raises(RuntimeError, match="llm.glm"):
        load_connection(settings)


def test_a_missing_settings_file_is_reported(project):
    with pytest.raises(RuntimeError, match="not found"):
        load_connection({"env_from_ps1": str(project / "absent.ps1")})


def test_glm_uses_the_claude_cli_with_the_connection(process, glm_configured):
    assert GLMClient().generate("question") == "answer"

    call = process.calls[0]
    assert call["command"][0] == "C:/bin/claude.cmd"
    assert call["command"][1] == "-p"
    assert call["command"][call["command"].index("--model") + 1] == "opus"
    assert call["env"]["ANTHROPIC_AUTH_TOKEN"] == FAKE_TOKEN
    assert call["env"]["ANTHROPIC_BASE_URL"] == FAKE_URL


def test_glm_secrets_stay_out_of_the_command_and_this_process(process, glm_configured):
    GLMClient().generate("question")

    assert FAKE_TOKEN not in " ".join(process.calls[0]["command"])
    assert FAKE_TOKEN not in process.calls[0]["input"]
    assert os.environ.get("ANTHROPIC_AUTH_TOKEN") != FAKE_TOKEN


def test_glm_does_not_send_an_inherited_api_key_to_its_endpoint(process, glm_configured, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key-for-a-different-service")

    GLMClient().generate("question")

    assert "ANTHROPIC_API_KEY" not in process.calls[0]["env"]


def test_glm_keeps_the_rest_of_the_environment(process, glm_configured, monkeypatch):
    monkeypatch.setenv("SOME_OTHER_VARIABLE", "kept")

    GLMClient().generate("question")

    assert process.calls[0]["env"]["SOME_OTHER_VARIABLE"] == "kept"


def test_glm_errors_never_show_the_token(process, glm_configured):
    process.result = Completed("", returncode=1, stderr=f"auth failed for {FAKE_TOKEN} at {FAKE_URL}")

    with pytest.raises(RuntimeError) as caught:
        GLMClient().generate("question")

    assert FAKE_TOKEN not in str(caught.value)
    assert "(hidden)" in str(caught.value)


def test_plain_claude_gets_no_special_environment(process, glm_configured):
    ClaudeCLIClient(command="claude").generate("question")

    assert process.calls[0]["env"] is None


def test_glm_availability_needs_the_connection(project, monkeypatch):
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: name)

    assert GLMClient.check_availability() is False

    configure(project, f"llm:\n  glm:\n    env_from_ps1: {ps1_file(project).as_posix()}\n")

    assert GLMClient.check_availability() is True


def test_glm_availability_needs_the_cli(glm_configured, monkeypatch):
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: None)

    assert GLMClient.check_availability() is False


# --- the factory -------------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        ("codex-cli", CodexCLIClient),
        ("codex", CodexCLIClient),
        ("antigravity-cli", AntigravityCLIClient),
        ("antigravity", AntigravityCLIClient),
        ("agy", AntigravityCLIClient),
        ("Claude-CLI", ClaudeCLIClient),
    ],
)
def test_names_and_aliases(process, name, expected):
    assert isinstance(LLMClient(provider=name), expected)


def test_factory_creates_glm(process, glm_configured):
    assert isinstance(LLMClient(provider="glm"), GLMClient)


def test_config_may_use_an_alias(project, process):
    configure(project, "llm:\n  provider: agy\n")

    assert LLMClient.get_provider() == "antigravity-cli"
    assert isinstance(LLMClient(), AntigravityCLIClient)


def test_unknown_provider_lists_what_is_supported():
    with pytest.raises(ValueError, match="codex-cli"):
        LLMClient(provider="nonsense")


@pytest.fixture
def only_available(monkeypatch):
    def set_available(*names):
        monkeypatch.setattr(
            LLMClient,
            "check_availability",
            classmethod(lambda cls, provider=None: provider in names),
        )

    return set_available


@pytest.mark.parametrize(
    "available, expected",
    [
        (("codex-cli", "ollama"), "codex-cli"),
        (("antigravity-cli", "ollama"), "antigravity-cli"),
        (("codex-cli", "antigravity-cli"), "codex-cli"),
        (("claude-cli", "codex-cli"), "claude-cli"),
        (("ollama",), "ollama"),
    ],
)
def test_fallback_order(only_available, available, expected):
    only_available(*available)

    assert LLMClient.get_provider() == expected


def test_glm_is_never_chosen_automatically(only_available):
    only_available("glm")

    assert LLMClient.get_provider() != "glm"
    assert "glm" not in LLMClient.PROVIDER_ORDER


def test_a_configured_glm_is_listed_and_used(project, only_available):
    only_available("glm", "claude-cli")
    configure(project, "llm:\n  provider: glm\n")

    assert LLMClient.get_provider() == "glm"
    assert LLMClient.list_available_providers() == ["claude-cli", "glm"]


# --- gemini-cli is gone ------------------------------------------------------


def test_gemini_cli_is_refused_with_the_replacement():
    with pytest.raises(ValueError, match="antigravity-cli"):
        LLMClient(provider="gemini-cli")


def test_gemini_cli_is_not_available_and_not_listed(monkeypatch):
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: name)

    assert LLMClient.check_availability("gemini-cli") is False
    assert "gemini-cli" not in LLMClient.list_available_providers()


def test_a_config_naming_gemini_explains_itself(project, capsys):
    configure(project, "llm:\n  provider: gemini-cli\n")

    print_llm_unavailable(console)

    output = " ".join(capsys.readouterr().out.split())
    assert "gemini-cli provider was removed" in output
    assert "antigravity-cli" in output


def test_mask_reports_the_canonical_provider_for_an_alias():
    assert LLMClient.normalize("codex") == "codex-cli"
    assert LLMClient.normalize("AGY") == "antigravity-cli"


def test_mask_explains_a_config_naming_gemini(project):
    configure(project, "llm:\n  provider: gemini-cli\n")

    with pytest.raises(RuntimeError, match="antigravity-cli"):
        MemoryAgent(project).ask("question")


def test_no_llm_message_names_the_new_providers(capsys):
    print_llm_unavailable(console)

    output = " ".join(capsys.readouterr().out.split())
    for expected in ("codex", "agy", "codex-cli", "antigravity-cli", "glm"):
        assert expected in output
    assert "gemini" not in output.lower()
