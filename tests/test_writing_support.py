"""Tests for writing guides, the mt-write skill and from-text."""

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.core.ai_module_generator import AIModuleGenerator, GeneratedModule
from memory_tool.core.init import MemoryInitializer
from memory_tool.core.module import ModuleManager
from memory_tool.core.writing_guides import (
    DOCUMENT_TYPES,
    GuideError,
    guide_file_name,
    read_all_guides,
    read_guide,
)
from memory_tool.llm.client import LLMClient
from memory_tool.utils.frontmatter import Frontmatter
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
def base(project):
    return project / ".memory"


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate(self, prompt, system_prompt=None, **kwargs):
        self.prompts.append(prompt)
        return self.response


ANSWER = """NAME: 합성 문서
TYPE: 판단
DESCRIPTION: 합성 설명입니다.
CONNECTIONS: existing, not-a-real-document
REASONING: 결론이 있어서입니다.
<<<BODY
결론은 합성입니다.

NAME: this line belongs to the body
BODY>>>"""


# --- guides ------------------------------------------------------------------


@pytest.mark.parametrize("doc_type", list(DOCUMENT_TYPES))
def test_every_type_has_a_guide_naming_itself(doc_type):
    assert f"# {doc_type} 문서 가이드" in read_guide(doc_type)


def test_common_guide_is_the_default_and_sets_the_order():
    text = read_guide()

    for step in ("질문", "작성 후 지적", "막힐 때 개요", "요청 시 대신 작성"):
        assert step in text
    for doc_type in DOCUMENT_TYPES:
        assert doc_type in text


@pytest.mark.parametrize(
    "asked, expected",
    [(None, "common"), ("판단", "judgment"), ("judgment", "judgment"), (" METHOD ", "method")],
)
def test_guide_names(asked, expected):
    assert guide_file_name(asked) == expected


def test_unknown_guide_names_the_types():
    with pytest.raises(GuideError, match="참고"):
        read_guide("회고")


def test_a_users_guide_takes_precedence(base):
    (base / "guides").mkdir()
    (base / "guides" / "judgment.md").write_text("내 판단 가이드", encoding="utf-8")

    assert read_guide("판단", base) == "내 판단 가이드"
    assert "참고 문서 가이드" in read_guide("참고", base)


def test_guides_are_not_written_into_new_documents(base, project):
    path = ModuleManager(project).create("topic", doc_type="판단")

    assert "가이드" not in path.read_text(encoding="utf-8")


def test_guides_do_not_assume_goal_loop_exists():
    assert "Goal Loop" not in read_all_guides()


def test_guide_command():
    result = runner.invoke(app, ["module", "guide"])

    assert result.exit_code == 0, result.output
    assert "문서 작성 가이드" in result.output


def test_guide_command_for_a_type_takes_it_as_the_name():
    result = runner.invoke(app, ["module", "guide", "판단"])

    assert result.exit_code == 0, result.output
    assert "판단 문서 가이드" in result.output


def test_guide_command_keeps_markup_like_text_intact(base):
    (base / "guides").mkdir()
    (base / "guides" / "common.md").write_text("[[링크]] [bold]그대로[/bold]", encoding="utf-8")

    result = runner.invoke(app, ["module", "guide"])

    assert "[[링크]] [bold]그대로[/bold]" in result.output


def test_guide_command_reports_an_unknown_guide():
    result = runner.invoke(app, ["module", "guide", "회고"])

    assert result.exit_code != 0
    assert "참고" in result.output


# --- skill -------------------------------------------------------------------


def test_minit_installs_the_writing_skill(project):
    created = MemoryInitializer(project).create_claude_skills()

    skill = project / ".claude" / "skills" / "mt-write" / "SKILL.md"
    assert skill in created
    assert "mmodule guide" in skill.read_text(encoding="utf-8")


# --- from-text ---------------------------------------------------------------


def generator(project, response=ANSWER):
    return AIModuleGenerator(FakeLLM(response), project)


def test_prompt_uses_the_guides_and_no_old_format(project):
    subject = generator(project)
    subject.generate("합성 입력")
    prompt = subject.llm_client.prompts[0]

    assert "합성 입력" in prompt
    assert "판단 문서 가이드" in prompt
    for retired in ("module.md", "current.md", "decisions.md", "Feature-based", "Topic-based"):
        assert retired not in prompt


def test_prompt_uses_a_users_guide(project, base):
    (base / "guides").mkdir()
    (base / "guides" / "judgment.md").write_text("내가 고친 판단 가이드", encoding="utf-8")
    subject = generator(project)

    subject.generate("합성 입력")

    assert "내가 고친 판단 가이드" in subject.llm_client.prompts[0]


def test_answer_is_parsed(project):
    ModuleManager(project).create("existing")

    generated = generator(project).generate("합성 입력")

    assert generated.name == "합성 문서"
    assert generated.doc_type == "판단"
    assert generated.description == "합성 설명입니다."
    assert generated.reasoning == "결론이 있어서입니다."
    assert generated.suggested_connections == ["existing"]
    assert "this line belongs to the body" in generated.body


def test_an_answer_wrapped_in_a_code_fence_is_read(project):
    generated = generator(project, f"```markdown\n{ANSWER}\n```").generate("합성 입력")

    assert generated.name == "합성 문서"


@pytest.mark.parametrize(
    "response",
    ["no format at all", "NAME: x\nTYPE: 참고\n", "TYPE: 참고\n<<<BODY\nbody\nBODY>>>"],
)
def test_an_unreadable_answer_fails_rather_than_saving_nonsense(project, response):
    with pytest.raises(ValueError):
        generator(project, response).generate("합성 입력")


def test_empty_input_is_refused_without_calling_the_llm(project):
    subject = generator(project)

    with pytest.raises(ValueError):
        subject.generate("   ")

    assert subject.llm_client.prompts == []


def test_saved_as_one_document_marked_as_ai_written(project):
    ModuleManager(project).create("existing")
    subject = generator(project)

    path = subject.save_module(subject.generate("합성 입력"))

    assert path.name == "합성 문서.md"
    assert sorted(p.name for p in path.parent.glob("*.md")) == ["existing.md", "합성 문서.md"]

    metadata, body = Frontmatter.parse(path.read_text(encoding="utf-8"))
    assert metadata["type"] == "판단"
    assert metadata["generated"]["by"].startswith("memory-tool/")
    assert "결론은 합성입니다." in body
    assert "[[existing]]" in body
    assert "not-a-real-document" not in body


def test_saving_over_an_existing_document_is_refused(project):
    ModuleManager(project).create("합성 문서")
    subject = generator(project)

    with pytest.raises(ValueError, match="already exists"):
        subject.save_module(subject.generate("합성 입력"))


def test_preview_keeps_markup_like_text_intact(project):
    preview = generator(project).format_preview(
        GeneratedModule("n", None, "d", "[bold]본문[/bold]", [], "r")
    )

    assert "\\[bold]" in preview


@pytest.fixture
def llm_answers(monkeypatch):
    monkeypatch.setattr(LLMClient, "check_availability", classmethod(lambda cls, provider=None: True))
    real_init = AIModuleGenerator.__init__

    def init(self, llm_client=None, base_path=None):
        real_init(self, FakeLLM(ANSWER), base_path)

    monkeypatch.setattr(AIModuleGenerator, "__init__", init)


def test_from_text_command_saves(project, base, llm_answers):
    result = runner.invoke(app, ["module", "from-text", "--text", "합성 입력"])

    assert result.exit_code == 0, result.output
    assert (base / "modules" / "합성 문서.md").is_file()


def test_from_text_preview_saves_nothing(project, base, llm_answers):
    result = runner.invoke(app, ["module", "from-text", "--text", "합성 입력", "--preview"])

    assert result.exit_code == 0, result.output
    assert "not saved" in result.output
    assert not list((base / "modules").rglob("*.md"))


def test_from_text_structure_option_warns_that_it_is_ignored(project, llm_answers):
    result = runner.invoke(
        app, ["module", "from-text", "--text", "합성 입력", "--preview", "--structure", "feature"]
    )

    assert result.exit_code == 0, result.output
    assert "--structure" in result.output
