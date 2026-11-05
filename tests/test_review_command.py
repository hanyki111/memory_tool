"""Tests for the mreview command. All data is synthetic."""

import json
from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from memory_tool.commands.common import app
from memory_tool.review import store
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

runner = CliRunner()


class FakeClient:
    calls = 0
    answer = '{"proposals": [], "more": 0}'

    def __init__(self, *args, **kwargs):
        pass

    def generate(self, prompt, system_prompt=None, **kwargs):
        FakeClient.calls += 1
        return FakeClient.answer


def answer(count, more=0):
    today = f"{datetime.now():%Y-%m-%d}"
    return json.dumps({
        "proposals": [
            {"kind": "new", "title": f"Topic {n}", "target": None, "type": "참고",
             "why": "reason", "evidence": [today]}
            for n in range(1, count + 1)
        ],
        "more": more,
    })


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
    now = datetime.now()
    day = folder / "timeline" / "daily" / f"{now:%Y-%m}"
    day.mkdir(parents=True)
    (day / f"{now:%Y-%m-%d}.md").write_text("# T\n- 00:00 | synthetic [entry]\n", encoding="utf-8")
    clear_cache()
    FakeClient.calls = 0
    FakeClient.answer = answer(0)
    monkeypatch.setattr("memory_tool.llm.client.LLMClient", FakeClient)
    yield folder
    clear_cache()


def run(*args, input=None):
    return runner.invoke(app, ["review", *args], input=input)


def states(base):
    return [item.state for item in store.latest_review(base).items]


def finish_with_deferred(base, count):
    FakeClient.answer = answer(count)
    result = run(input="2\n" * count)
    assert result.exit_code == 0, result.output


def add_entry_now(base):
    """Add an entry the next review will see, since it starts at this minute."""
    now = datetime.now()
    path = base / "timeline" / "daily" / f"{now:%Y-%m}" / f"{now:%Y-%m-%d}.md"
    with path.open("a", encoding="utf-8") as file:
        file.write(f"- {now:%H:%M} | another entry\n")


class TestChoosing:
    def test_three_choices_for_a_new_proposal(self, base):
        FakeClient.answer = answer(3)

        result = run(input="2\n3\n2\n")

        assert result.exit_code == 0, result.output
        assert states(base) == [store.STATE_DEFERRED, store.STATE_REJECTED, store.STATE_DEFERRED]
        assert store.latest_review(base).is_done
        assert "Topic 1" in result.output
        assert "Write later" in result.output

    def test_invalid_answer_asks_again(self, base):
        FakeClient.answer = answer(1)

        result = run(input="9\n3\n")

        assert result.exit_code == 0, result.output
        assert states(base) == [store.STATE_REJECTED]

    def test_notes_candidates_left_out(self, base):
        FakeClient.answer = answer(1, more=4)

        result = run(input="3\n")

        assert "4 more candidates" in result.output

    def test_nothing_to_review(self, base):
        for path in (base / "timeline").rglob("*.md"):
            path.unlink()

        result = run()

        assert result.exit_code == 0
        assert "No new entries" in result.output
        assert store.review_files(base) == []

    def test_failed_proposal_reports_and_writes_nothing(self, base, monkeypatch):
        FakeClient.answer = "not json"

        result = run()

        assert result.exit_code == 1
        assert "did not start" in result.output
        assert store.review_files(base) == []

    def test_invalid_since(self, base):
        result = run("--since", "someday")

        assert result.exit_code == 1
        assert FakeClient.calls == 0

    def test_since_is_used(self, base):
        result = run("--since", f"{datetime.now() - timedelta(days=40):%Y-%m-%d}")

        assert result.exit_code == 0, result.output
        expected = f"{datetime.now() - timedelta(days=40):%Y-%m-%d}T00:00"
        assert store.latest_review(base).start == expected


class TestDeferLimit:
    def test_cannot_put_off_until_five_remain(self, base):
        finish_with_deferred(base, 3)
        add_entry_now(base)
        FakeClient.answer = answer(5)

        # Eight are open. The first three go, so the rest may wait.
        result = run(input="2\n2\n1\n2\n2\n2\n2\n2\n")

        assert result.exit_code == 0, result.output
        assert "nothing can be put off" in result.output
        assert len(store.latest_review(base).open_items()) == 5


class TestPausing:
    def test_pause_keeps_the_choices_and_the_proposals(self, base):
        FakeClient.answer = answer(2)

        first = run(input="3\np\n")

        assert first.exit_code == 0, first.output
        assert "Paused" in first.output
        review = store.latest_review(base)
        assert not review.is_done
        assert states(base) == [store.STATE_REJECTED, store.STATE_PROPOSED]

        FakeClient.answer = answer(5)
        second = run(input="3\n")

        assert second.exit_code == 0, second.output
        assert FakeClient.calls == 1
        assert states(base) == [store.STATE_REJECTED, store.STATE_REJECTED]
        assert store.latest_review(base).is_done

    def test_input_ending_counts_as_a_pause(self, base):
        FakeClient.answer = answer(2)

        result = run(input="3\n")

        assert result.exit_code == 0, result.output
        assert states(base) == [store.STATE_REJECTED, store.STATE_PROPOSED]
        assert not store.latest_review(base).is_done

    def test_since_is_ignored_during_a_review(self, base):
        FakeClient.answer = answer(1)
        run(input="p\n")
        start = store.latest_review(base).start

        result = run("--since", "2020-01-01", input="3\n")

        assert "--since is ignored" in result.output
        assert store.latest_review(base).start == start


class TestCarriedItems:
    def test_carried_items_come_first_with_their_choices(self, base):
        finish_with_deferred(base, 1)
        add_entry_now(base)
        FakeClient.answer = answer(1)

        result = run(input="1\n3\n")

        assert result.exit_code == 0, result.output
        assert "Put off in an earlier review" in result.output
        assert "Keep for later" in result.output
        assert states(base) == [store.STATE_WRITTEN, store.STATE_REJECTED]


class TestListAndDone:
    def test_list_shows_what_waits(self, base):
        finish_with_deferred(base, 2)

        result = run("list")

        assert "1. [later]" in result.output
        assert "Topic 2" in result.output

    def test_list_when_empty(self, base):
        assert "Nothing is waiting" in run("list").output

    def test_done_settles_an_item(self, base):
        finish_with_deferred(base, 2)

        result = run("done", "2")

        assert result.exit_code == 0, result.output
        assert states(base) == [store.STATE_DEFERRED, store.STATE_WRITTEN]
        assert "Topic 2" not in run("list").output

    def test_done_of_a_missing_item(self, base):
        finish_with_deferred(base, 1)

        assert run("done", "9").exit_code == 1

    def test_done_without_a_review(self, base):
        assert run("done", "1").exit_code == 1
