"""Tests for document health: one set of thresholds, and a hook about the commit.

The hook checked every document, so a knowledge base kept out of git warned on
every commit, and single documents were judged against the legacy current.md
budget. All data is synthetic.
"""

import shutil
import subprocess

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.utils.health_checker import DocumentHealthChecker
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


def write(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("line\n" * lines, encoding="utf-8")
    return path


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    folder = tmp_path / ".memory"
    (folder / "modules").mkdir(parents=True)
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    yield folder
    clear_cache()


def severities(base):
    return {issue.display_path: issue.severity for issue in DocumentHealthChecker(base).check_all_modules()}


class TestThresholds:
    def test_a_single_document_gets_the_combined_budget(self, base):
        write(base / "modules" / "a" / "a.md", 599)
        write(base / "modules" / "b" / "b.md", 700)
        write(base / "modules" / "c.md", 1000)

        assert severities(base) == {"b/b.md": "warning", "c.md": "critical"}

    def test_legacy_files_keep_their_budgets(self, base):
        write(base / "modules" / "old" / "module.md", 450)
        write(base / "modules" / "old" / "decisions.md", 350)

        issues = DocumentHealthChecker(base).check_all_modules()

        assert {(i.module_name, i.display_path, i.severity) for i in issues} == {
            ("old", "old/module.md", "critical"),
            ("old", "old/decisions.md", "warning"),
        }

    def test_archive_command_never_names_the_document_type(self, base):
        write(base / "modules" / "topic.md", 1200)
        write(base / "modules" / "old" / "current.md", 450)

        commands = {i.display_path: i.archive_command for i in DocumentHealthChecker(base).check_all_modules()}

        assert commands == {
            "topic.md": "marchive decisions --module topic",
            "old/current.md": "marchive current --module old",
        }

    def test_only_limits_the_check_to_the_given_files(self, base):
        big = write(base / "modules" / "big.md", 1200)
        write(base / "modules" / "other.md", 1200)

        issues = DocumentHealthChecker(base).check_all_modules(only=[big])

        assert [issue.display_path for issue in issues] == ["big.md"]

    def test_context_agrees_with_the_checker(self, base):
        from memory_tool.context.builder import ContextBuilder

        write(base / "modules" / "topic.md", 700)

        content = ContextBuilder(base.parent).build_context_content()

        assert "**topic.md**: 700 lines" in content
        assert "topic/topic.md" not in content
        assert "WARNING" in content and "CRITICAL" not in content


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@needs_git
class TestHook:
    @pytest.fixture
    def repo(self, base):
        root = base.parent
        git("init", "-q", cwd=root)
        git("config", "user.email", "test@example.com", cwd=root)
        git("config", "user.name", "test", cwd=root)
        return root

    def check(self):
        return runner.invoke(app, ["context", "--check-health-only"])

    def test_quiet_when_the_knowledge_base_is_not_committed(self, base, repo):
        (repo / ".gitignore").write_text(".memory\n", encoding="utf-8")
        write(base / "modules" / "huge.md", 5000)
        (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
        git("add", ".", cwd=repo)

        result = self.check()

        assert result.exit_code == 0, result.output

    def test_warns_about_a_large_document_being_committed(self, base, repo):
        write(base / "modules" / "huge.md", 5000)
        write(base / "modules" / "untouched.md", 5000)
        git("add", ".memory/modules/huge.md", cwd=repo)

        result = self.check()

        assert result.exit_code == 2
        assert "huge.md: 5000 lines" in result.output
        assert "untouched" not in result.output
        assert "module.md" not in result.output
        assert "marchive decisions --module huge --interactive" in result.output

    def test_checks_everything_outside_a_repository(self, base, monkeypatch):
        monkeypatch.setattr("memory_tool.commands.context._staged_files", lambda: None)
        write(base / "modules" / "huge.md", 5000)

        assert self.check().exit_code == 2
