"""Tests for the review notice. All data is synthetic."""

from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.context.builder import ContextBuilder
from memory_tool.review import store
from memory_tool.review.notice import review_notice
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()
NOW = datetime(2026, 10, 20, 9, 0)


@pytest.fixture(autouse=True)
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


def add_entries(base, day, count):
    folder = base / "timeline" / "daily" / f"{day:%Y-%m}"
    folder.mkdir(parents=True, exist_ok=True)
    lines = "".join(f"- 10:{n:02d} | entry {n}\n" for n in range(count))
    (folder / f"{day:%Y-%m-%d}.md").write_text(f"# T\n{lines}", encoding="utf-8")


def finished_review(base, end):
    review = store.start_review(base, f"{end:%Y-%m-%d}", "2026-01-01T00:00", f"{end:%Y-%m-%dT%H:%M}", [])
    review.status = store.STATUS_DONE
    store.save_review(review)
    return review


def set_config(base, text):
    (base / "config.yaml").write_text(f"version: '1.0'\n{text}", encoding="utf-8")
    clear_cache()


class TestConditions:
    def test_due_after_enough_days_and_entries(self, base):
        finished_review(base, NOW - timedelta(days=7))
        add_entries(base, NOW - timedelta(days=3), 10)

        notice = review_notice(base, NOW)

        assert "7 days" in notice
        assert "10 entries" in notice

    def test_too_few_days(self, base):
        finished_review(base, NOW - timedelta(days=6))
        add_entries(base, NOW - timedelta(days=3), 30)

        assert review_notice(base, NOW) is None

    def test_too_few_entries(self, base):
        finished_review(base, NOW - timedelta(days=30))
        add_entries(base, NOW - timedelta(days=3), 9)

        assert review_notice(base, NOW) is None

    def test_first_review_needs_only_entries(self, base):
        add_entries(base, NOW - timedelta(days=3), 10)

        assert "No review yet" in review_notice(base, NOW)

    def test_first_review_ignores_entries_outside_its_window(self, base):
        add_entries(base, NOW - timedelta(days=30), 50)

        assert review_notice(base, NOW) is None

    def test_review_in_progress_is_always_mentioned(self, base):
        store.start_review(base, "2026-10-19", "2026-10-01T00:00", "2026-10-19T09:00", [])

        assert "in progress" in review_notice(base, NOW)

    def test_values_can_be_changed(self, base):
        set_config(base, "review:\n  notice:\n    min_days: 1\n    min_entries: 2\n")
        finished_review(base, NOW - timedelta(days=1))
        add_entries(base, NOW, 2)

        assert review_notice(base, NOW.replace(hour=23)) is not None

    def test_can_be_turned_off(self, base):
        set_config(base, "review:\n  notice:\n    enabled: false\n")
        add_entries(base, NOW, 50)

        assert review_notice(base, NOW) is None

    def test_unusable_value_falls_back(self, base):
        set_config(base, "review:\n  notice:\n    min_entries: many\n")
        add_entries(base, NOW, 9)

        assert review_notice(base, NOW) is None

    def test_unreadable_review_file_gives_no_notice(self, base):
        folder = store.reviews_folder(base)
        folder.mkdir()
        (folder / "2026-10-01.md").write_text("# hand-edited\n", encoding="utf-8")

        assert review_notice(base, NOW) is None


class TestRecording:
    @pytest.fixture
    def due(self, base):
        """Yesterday holds enough entries, and today has none yet."""
        add_entries(base, datetime.now() - timedelta(days=1), 12)

    def test_shown_on_the_days_first_entry_only(self, base, due):
        first = runner.invoke(app, ["record", "first"])
        second = runner.invoke(app, ["record", "second"])

        assert first.exit_code == 0, first.output
        assert "Run mreview" in first.output
        assert "Run mreview" not in second.output

    def test_not_shown_for_an_entry_on_a_past_date(self, base, due):
        past = f"{datetime.now() - timedelta(days=2):%Y-%m-%d}"

        result = runner.invoke(app, ["record", "late", "--date", past, "--force"])

        assert result.exit_code == 0, result.output
        assert "Run mreview" not in result.output

    def test_a_failure_does_not_stop_the_record(self, base, due, monkeypatch):
        def broken(*args):
            raise RuntimeError("boom")

        monkeypatch.setattr("memory_tool.review.notice.review_notice", broken)

        result = runner.invoke(app, ["record", "still saved"])

        assert result.exit_code == 0, result.output
        today = datetime.now()
        path = base / "timeline" / "daily" / f"{today:%Y-%m}"
        assert any("still saved" in p.read_text(encoding="utf-8") for p in path.glob("*.md"))


class TestContext:
    def test_context_carries_the_notice_when_due(self, base):
        add_entries(base, datetime.now() - timedelta(days=1), 12)

        content = ContextBuilder().build_context_content()

        assert "## Review" in content
        assert "Run mreview" in content

    def test_context_is_silent_otherwise(self, base):
        assert "## Review" not in ContextBuilder().build_context_content()
