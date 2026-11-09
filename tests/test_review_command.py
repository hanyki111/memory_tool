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

    # A test must never start a real CLI or editor. FakeTools replaces these.
    def no_real_process(*args, **kwargs):
        raise AssertionError(f"A test tried to start a process: {args}")

    monkeypatch.setattr("memory_tool.review.writer.shutil.which", lambda name: None)
    monkeypatch.setattr("memory_tool.review.writer.subprocess.run", no_real_process)
    yield folder
    clear_cache()


def run_raw(*args, input=None):
    return runner.invoke(app, ["review", *args], input=input)


def run(*args, input=None):
    """Run a review, going straight past the reflection menu to the items.

    Only for tests about the items. "s" is simply asked again at any later menu,
    so it does no harm if the reflection was settled already.
    """
    starts_a_review = not args or args[0].startswith("--")
    if input is not None and starts_a_review:
        input = "s\n" + input
    return run_raw(*args, input=input)


def states(base):
    return [item.state for item in store.latest_review(base).items]


def finish_with_deferred(base, count):
    FakeClient.answer = answer(count)
    result = run(input="2\n" * count)
    assert result.exit_code == 0, result.output
    assert store.latest_review(base).is_done


def add_entry_now(base):
    """Add an entry the next review will see, since it starts at this minute."""
    now = datetime.now()
    path = base / "timeline" / "daily" / f"{now:%Y-%m}" / f"{now:%Y-%m-%d}.md"
    with path.open("a", encoding="utf-8") as file:
        file.write(f"- {now:%H:%M} | another entry\n")


class TestChoosing:
    def test_three_choices_for_a_new_proposal(self, base):
        FakeClient.answer = answer(3)

        result = run(input="2\n3\n2\ns\n")

        assert result.exit_code == 0, result.output
        assert states(base) == [store.STATE_DEFERRED, store.STATE_REJECTED, store.STATE_DEFERRED]
        assert store.latest_review(base).is_done
        assert "Topic 1" in result.output
        assert "Write later" in result.output

    def test_each_step_says_what_it_is_for(self, base):
        FakeClient.answer = answer(1)

        result = run(input="3\n")

        assert "Reflection: go over" in result.output
        assert "To keep: for each" in result.output

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

    def test_failed_proposal_can_be_tried_again_later(self, base):
        FakeClient.answer = "not json"

        result = run(input="p\n")

        assert result.exit_code == 0, result.output
        assert "Could not get proposals" in result.output
        assert store.latest_review(base).proposals_pending

        FakeClient.answer = answer(1)
        result = run(input="3\n")

        assert result.exit_code == 0, result.output
        assert store.latest_review(base).is_done
        assert states(base) == [store.STATE_REJECTED]

    def test_going_on_without_candidates_finishes(self, base):
        FakeClient.answer = "not json"

        result = run(input="c\n")

        assert result.exit_code == 0, result.output
        review = store.latest_review(base)
        assert review.is_done
        assert not review.proposals_pending

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
        # Three repeat the carried titles, so five of these are new.
        FakeClient.answer = answer(8)

        # Eight are open. The first three go, so the rest may wait.
        result = run(input="2\n2\n1\n2\n2\n2\n2\n2\ns\n")

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
        second = run(input="3\ns\n")

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
        # The first repeats the carried title, so only the second is new.
        FakeClient.answer = answer(2)

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


class FakeTools:
    """Pretend the CLIs are installed and record how they are started."""

    def __init__(self, monkeypatch, installed=("claude", "codex", "agy")):
        self.calls = []
        self.work_files = []
        monkeypatch.setattr(
            "memory_tool.review.writer.shutil.which",
            lambda name: f"/bin/{name}" if name in installed else None,
        )
        monkeypatch.setattr("memory_tool.review.writer.subprocess.run", self.run)

    def run(self, arguments, cwd=None, **kwargs):
        self.calls.append((arguments, cwd))
        if cwd is not None:
            relative = arguments[-1].split("Read the file ")[1].split(" and follow")[0]
            path = cwd / relative
            self.work_files.append((path, path.read_text(encoding="utf-8")))


class TestWriting:
    def test_menu_lists_installed_tools_and_defaults_to_the_first(self, base, monkeypatch):
        tools = FakeTools(monkeypatch, installed=("codex", "agy"))
        FakeClient.answer = answer(1)

        # Write now, accept the default tool, then say it was written.
        result = run(input="1\n\n1\n")

        assert result.exit_code == 0, result.output
        assert "Claude Code" not in result.output
        assert "1. Codex (default)" in result.output
        assert "3. On my own" in result.output
        assert tools.calls[0][0][0] == "/bin/codex"
        assert states(base) == [store.STATE_WRITTEN]

    def test_each_tool_gets_its_own_way_of_starting(self, base, monkeypatch):
        tools = FakeTools(monkeypatch)
        finish_with_deferred(base, 3)

        for number, name in ((1, "claude"), (2, "codex"), (3, "antigravity")):
            assert run("write", str(number), "--with", name, input="1\n").exit_code == 0

        assert [call[0][0] for call in tools.calls] == ["/bin/claude", "/bin/codex", "/bin/agy"]
        assert tools.calls[0][0][1].startswith("Read the file")
        assert tools.calls[1][0][1].startswith("Read the file")
        assert tools.calls[2][0][1] == "-i"
        assert all(call[1].resolve() == base.parent.resolve() for call in tools.calls)

    def test_never_skips_permission_prompts(self, base, monkeypatch):
        tools = FakeTools(monkeypatch)
        finish_with_deferred(base, 1)

        run("write", "1", "--with", "codex", input="1\n")

        assert not any("skip" in part or "bypass" in part for part in tools.calls[0][0])

    def test_instruction_stays_short_and_the_work_file_carries_the_context(self, base, monkeypatch):
        tools = FakeTools(monkeypatch)
        finish_with_deferred(base, 1)

        run("write", "1", "--with", "claude", input="1\n")

        assert len(tools.calls[0][0][-1]) < 300
        path, content = tools.work_files[0]
        assert "MT-Write" in content
        assert "Topic 1" in content
        assert "synthetic [entry]" in content
        assert not path.exists()

    def test_project_copy_of_the_procedure_wins(self, base, monkeypatch):
        tools = FakeTools(monkeypatch)
        own = base.parent / ".claude" / "skills" / "mt-write" / "SKILL.md"
        own.parent.mkdir(parents=True)
        own.write_text("MY PROCEDURE", encoding="utf-8")
        finish_with_deferred(base, 1)

        run("write", "1", "--with", "claude", input="1\n")

        assert "MY PROCEDURE" in tools.work_files[0][1]

    def test_item_stays_open_until_marked_written(self, base, monkeypatch):
        FakeTools(monkeypatch)
        FakeClient.answer = answer(1)

        # Write now, then "still writing".
        result = run("--with", "claude", input="1\n2\n")

        assert result.exit_code == 0, result.output
        review = store.latest_review(base)
        assert states(base) == [store.STATE_WRITING]
        assert not review.is_done

        second = run(input="1\ns\n")

        assert second.exit_code == 0, second.output
        assert "You were writing this" in second.output
        assert store.latest_review(base).is_done

    def test_write_later_makes_no_file_until_writing_starts(self, base, monkeypatch):
        monkeypatch.setattr("memory_tool.review.writer.open_in_editor", lambda path: None)
        FakeTools(monkeypatch)
        finish_with_deferred(base, 1)
        assert list((base / "modules").rglob("*.md")) == []

        result = run("write", "1", "--with", "solo", input="backup-reason\n1\n")

        assert result.exit_code == 0, result.output
        assert list((base / "modules").rglob("backup-reason.md"))
        assert "synthetic [entry]" in result.output
        assert states(base) == [store.STATE_WRITTEN]

    def test_solo_update_opens_the_existing_document(self, base, monkeypatch):
        opened = []
        monkeypatch.setattr("memory_tool.review.writer.open_in_editor", opened.append)
        FakeTools(monkeypatch)
        (base / "modules" / "server.md").write_text("# server\n", encoding="utf-8")
        today = f"{datetime.now():%Y-%m-%d}"
        FakeClient.answer = json.dumps({"proposals": [
            {"kind": "update", "title": "Port", "target": "server", "evidence": [today]}
        ]})

        result = run("--with", "solo", input="1\n1\n")

        assert result.exit_code == 0, result.output
        # --with also chooses how to reflect, so the review file opens first.
        assert opened[-1].name == "server.md"

    def test_solo_asks_again_for_an_invalid_path(self, base, monkeypatch):
        monkeypatch.setattr("memory_tool.review.writer.open_in_editor", lambda path: None)
        FakeTools(monkeypatch)
        finish_with_deferred(base, 1)

        result = run("write", "1", "--with", "solo", input="../bad\ngood\n1\n")

        assert result.exit_code == 0, result.output
        assert states(base) == [store.STATE_WRITTEN]

    def test_unknown_or_missing_tool_changes_nothing(self, base, monkeypatch):
        FakeTools(monkeypatch, installed=("claude",))
        finish_with_deferred(base, 1)

        assert run("write", "1", "--with", "vim").exit_code == 1
        assert run("write", "1", "--with", "codex").exit_code == 1
        assert states(base) == [store.STATE_DEFERRED]

    def test_writing_a_settled_item_is_refused(self, base, monkeypatch):
        FakeTools(monkeypatch)
        finish_with_deferred(base, 1)
        run("done", "1")

        assert run("write", "1", "--with", "claude").exit_code == 1

    def test_configured_writer_is_the_default(self, base, monkeypatch):
        FakeTools(monkeypatch)
        (base / "config.yaml").write_text(
            "version: '1.0'\nreview:\n  writer: codex\n", encoding="utf-8"
        )
        clear_cache()
        FakeClient.answer = answer(1)

        result = run(input="1\n\n1\n")

        assert "2. Codex (default)" in result.output

    def test_llm_provider_is_the_next_default(self, base, monkeypatch):
        FakeTools(monkeypatch)
        (base / "config.yaml").write_text(
            "version: '1.0'\nllm:\n  provider: antigravity-cli\n", encoding="utf-8"
        )
        clear_cache()
        FakeClient.answer = answer(1)

        result = run(input="1\n\n1\n")

        assert "3. Antigravity (default)" in result.output

    def test_left_as_being_written_after_the_review_ended(self, base, monkeypatch):
        FakeTools(monkeypatch)
        finish_with_deferred(base, 1)

        result = run("write", "1", "--with", "claude", input="2\n")

        assert result.exit_code == 0, result.output
        assert "Left as being written" in result.output
        assert states(base) == [store.STATE_WRITING]


class TestJson:
    def payload(self, result):
        return json.loads(result.output.strip())

    def test_starts_a_review_and_prints_it_on_one_line(self, base):
        FakeClient.answer = answer(2)

        result = run("--json")

        assert result.exit_code == 0, result.output
        assert len(result.output.strip().splitlines()) == 1
        review = self.payload(result)["review"]
        assert review["status"] == "in_progress"
        assert review["can_defer"] is True
        assert [item["title"] for item in review["items"]] == ["Topic 1", "Topic 2"]

    def test_reads_the_review_in_progress_without_calling(self, base):
        FakeClient.answer = answer(1)
        run("--json")

        result = run("--json")

        assert FakeClient.calls == 1
        assert self.payload(result)["ok"] is True

    def test_nothing_to_review(self, base):
        for path in (base / "timeline").rglob("*.md"):
            path.unlink()

        assert self.payload(run("--json")) == {"ok": True, "review": None}

    def test_failure_is_reported_as_json(self, base):
        FakeClient.answer = "not json"

        result = run("--json")

        assert result.exit_code == 1
        assert self.payload(result)["ok"] is False
        assert store.review_files(base) == []

    def test_choices_follow_the_same_rules(self, base):
        finish_with_deferred(base, 1)
        add_entry_now(base)
        FakeClient.answer = answer(5)
        run("--json")

        refused = run("set", "1", "later")

        assert refused.exit_code == 1
        assert self.payload(refused)["ok"] is False

        assert self.payload(run("set", "1", "reject"))["review"]["can_defer"] is True
        assert self.payload(run("set", "2", "later"))["review"]["items"][1]["state"] == "deferred"

    def test_write_only_marks_the_item(self, base, monkeypatch):
        tools = FakeTools(monkeypatch)
        FakeClient.answer = answer(1)
        run("--json")

        review = self.payload(run("set", "1", "write"))["review"]

        assert review["items"][0]["state"] == "writing"
        assert tools.calls == []

    def test_review_finishes_when_everything_is_settled(self, base):
        FakeClient.answer = answer(1)
        run("--json")

        assert self.payload(run("set", "1", "reject"))["review"]["status"] == "in_progress"
        assert self.payload(run("reflection", "skipped"))["review"]["status"] == "done"

    def test_unknown_values_are_refused(self, base):
        FakeClient.answer = answer(1)
        run("--json")

        assert run("set", "1", "maybe").exit_code == 1
        assert run("reflection", "maybe").exit_code == 1

    def test_list_as_json(self, base):
        finish_with_deferred(base, 2)

        items = self.payload(run("list", "--json"))["items"]

        assert [item["number"] for item in items] == [1, 2]

    def test_text_review_is_not_changed_by_json_settling(self, base):
        FakeClient.answer = answer(1)
        run("--json")
        run("set", "1", "reject")

        result = run(input="s\n")

        assert result.exit_code == 0, result.output
        assert store.latest_review(base).is_done


class TestReflection:
    def test_skipping_ends_the_review_with_the_fixed_question_left_as_a_comment(self, base):
        FakeClient.answer = answer(0)

        result = run(input="s\n")

        assert result.exit_code == 0, result.output
        review = store.latest_review(base)
        assert review.is_done
        assert review.reflection == store.REFLECTION_SKIPPED
        assert "<!-- What went well" in review.path.read_text(encoding="utf-8")

    def test_generates_no_questions_in_advance(self, base):
        FakeClient.answer = answer(0)
        run(input="s\n")

        assert FakeClient.calls == 1

    def test_not_offered_when_no_entries_were_read(self, base):
        finish_with_deferred(base, 1)
        # The next review has only the carried item, one minute later at most.
        for path in (base / "timeline").rglob("*.md"):
            path.unlink()

        result = run(input="3\n")

        assert result.exit_code == 0, result.output
        assert "Reflection" not in result.output
        assert store.latest_review(base).is_done

    def test_text_survives_a_removed_heading(self, base):
        FakeClient.answer = answer(1)
        run(input="p\n")
        review = store.latest_review(base)
        text = review.path.read_text(encoding="utf-8")
        review.path.write_text(text.replace("## Reflection", "") + "\nKeep me.\n", encoding="utf-8")

        store.save_review(store.load_review(review.path))

        assert "Keep me." in review.path.read_text(encoding="utf-8")


class TestSinceAfterLastReview:
    GAP_WARNINGS = ("will not be reviewed", "리뷰되지 않습니다")

    def warned(self, result):
        output = " ".join(result.output.split())
        return any(warning in output for warning in self.GAP_WARNINGS)

    def finish_a_review(self, base, end):
        review = store.start_review(base, "2026-10-01", "2026-09-01T00:00", end, [])
        review.status = store.STATUS_DONE
        store.save_review(review)

    def test_a_later_date_warns_about_the_gap(self, base):
        self.finish_a_review(base, "2026-10-01T12:00")

        assert self.warned(run("--since", "2030-01-01"))

    def test_an_earlier_date_leaves_nothing_out_and_does_not_warn(self, base):
        self.finish_a_review(base, "2026-10-01T12:00")

        assert not self.warned(run("--since", "2026-09-15"))

    def test_no_date_does_not_warn(self, base):
        self.finish_a_review(base, "2026-10-01T12:00")

        assert not self.warned(run())


class TestReflectionComesFirst:
    @pytest.fixture
    def tools(self, base, monkeypatch):
        FakeClient.answer = answer(0)
        return FakeTools(monkeypatch, installed=("claude",))

    def test_nothing_is_proposed_before_the_reflection(self, base, tools):
        run_raw(input="p\n")

        assert FakeClient.calls == 0
        assert store.latest_review(base).proposals_pending

    def test_pausing_returns_to_the_reflection(self, base, tools):
        assert run_raw(input="p\n").exit_code == 0
        assert not store.latest_review(base).is_done

        FakeClient.answer = answer(1)
        result = run_raw(input="s\n3\n")

        assert result.exit_code == 0, result.output
        assert store.latest_review(base).is_done
        assert len(store.review_files(base)) == 1

    def test_json_still_proposes_at_once(self, base):
        FakeClient.answer = answer(1)

        payload = json.loads(run_raw("--json").output.strip().splitlines()[-1])

        assert [item["title"] for item in payload["review"]["items"]] == ["Topic 1"]
        assert not store.latest_review(base).proposals_pending

    def test_json_fills_a_review_paused_before_its_candidates(self, base, tools):
        run_raw(input="p\n")
        FakeClient.answer = answer(1)

        payload = json.loads(run_raw("--json").output.strip().splitlines()[-1])

        assert [item["title"] for item in payload["review"]["items"]] == ["Topic 1"]

    def test_candidates_only_skips_the_conversation(self, base, tools):
        FakeClient.answer = answer(1)

        result = run_raw(input="s\n3\n")

        assert result.exit_code == 0, result.output
        assert tools.calls == []
        assert FakeClient.calls == 1
        review = store.latest_review(base)
        assert review.is_done
        assert review.reflection == store.REFLECTION_SKIPPED
        assert states(base) == [store.STATE_REJECTED]

    def test_enter_starts_the_default_tool_with_the_period_and_guide(self, base, tools):
        result = run_raw(input="\ns\n")

        assert result.exit_code == 0, result.output
        path, content = tools.work_files[0]
        assert "회고 가이드" in content
        assert "mreview add" in content
        assert "synthetic [entry]" in content
        assert store.latest_review(base).path.name in content
        assert not path.exists()

    def test_leaving_a_tool_with_nothing_done_asks_again(self, base, tools):
        result = run_raw(input="1\ns\n")

        assert result.exit_code == 0, result.output
        assert len(tools.calls) == 1
        assert store.latest_review(base).reflection == store.REFLECTION_SKIPPED

    def test_items_added_during_the_conversation_are_asked_about(self, base, monkeypatch, tools):
        def adds_an_item(arguments, cwd=None, **kwargs):
            assert run_raw("add", "Kept in conversation", "--why", "reason").exit_code == 0

        monkeypatch.setattr("memory_tool.review.writer.subprocess.run", adds_an_item)

        result = run_raw(input="1\n3\n")

        assert result.exit_code == 0, result.output
        review = store.latest_review(base)
        assert [item.title for item in review.items] == ["Kept in conversation"]
        assert review.items[0].state == store.STATE_REJECTED
        assert review.reflection == store.REFLECTION_WRITTEN
        assert FakeClient.calls == 0
        assert review.is_done

    def test_an_item_added_before_a_crash_stays(self, base, monkeypatch, tools):
        def adds_then_dies(arguments, cwd=None, **kwargs):
            run_raw("add", "Kept before the crash")
            raise KeyboardInterrupt

        monkeypatch.setattr("memory_tool.review.writer.subprocess.run", adds_then_dies)

        run_raw(input="1\n")

        review = store.latest_review(base)
        assert [item.title for item in review.items] == ["Kept before the crash"]
        assert not review.is_done

    def writes_text(self, base, monkeypatch):
        def write(arguments, cwd=None, **kwargs):
            path = store.latest_review(base).path
            with path.open("a", encoding="utf-8") as file:
                file.write("\nA synthetic reflection.\n")

        monkeypatch.setattr("memory_tool.review.writer.subprocess.run", write)

    def test_text_without_items_can_simply_finish(self, base, monkeypatch, tools):
        self.writes_text(base, monkeypatch)

        result = run_raw(input="1\n\n")

        assert result.exit_code == 0, result.output
        review = store.latest_review(base)
        assert review.is_done
        assert review.reflection == store.REFLECTION_WRITTEN
        assert review.items == []
        assert FakeClient.calls == 0
        assert "A synthetic reflection." in review.path.read_text(encoding="utf-8")

    def test_text_without_items_can_ask_for_candidates(self, base, monkeypatch, tools):
        self.writes_text(base, monkeypatch)
        FakeClient.answer = answer(1)

        result = run_raw(input="1\n2\n3\n")

        assert result.exit_code == 0, result.output
        assert FakeClient.calls == 1
        assert states(base) == [store.STATE_REJECTED]

    def test_text_without_items_can_add_one_by_hand(self, base, monkeypatch, tools):
        self.writes_text(base, monkeypatch)

        result = run_raw(input="1\na\nBy hand\n\n3\n")

        assert result.exit_code == 0, result.output
        assert [item.title for item in store.latest_review(base).items] == ["By hand"]


class TestReflectingAlone:
    @pytest.fixture
    def editor(self, base, monkeypatch):
        FakeClient.answer = answer(0)
        seen = {}

        def edit(path):
            seen["during"] = path.read_text(encoding="utf-8")
            if seen.get("write"):
                with path.open("a", encoding="utf-8") as file:
                    file.write(f"\n{seen['write']}\n")

        monkeypatch.setattr("memory_tool.review.writer.open_in_editor", edit)
        return seen

    def test_the_entries_are_shown_while_writing_and_gone_afterwards(self, base, editor):
        editor["write"] = "My own words."

        result = run_raw(input="1\n")

        assert result.exit_code == 0, result.output
        assert "synthetic [entry]" in editor["during"]
        content = store.latest_review(base).path.read_text(encoding="utf-8")
        assert "synthetic [entry]" not in content
        assert "My own words." in content

    def test_what_was_written_reaches_the_candidates(self, base, editor, monkeypatch):
        editor["write"] = "My own words."
        prompts = []
        original = FakeClient.generate

        def spy(self, prompt, system_prompt=None, **kwargs):
            prompts.append(prompt)
            return original(self, prompt, system_prompt, **kwargs)

        monkeypatch.setattr(FakeClient, "generate", spy)

        run_raw(input="1\n")

        assert "<reflection>" in prompts[0]
        assert "My own words." in prompts[0]
        assert "synthetic [entry]" in prompts[0]

    def test_closing_with_nothing_written_asks_again(self, base, editor):
        result = run_raw(input="1\ns\n")

        assert result.exit_code == 0, result.output
        assert store.latest_review(base).reflection == store.REFLECTION_SKIPPED

    def test_an_entry_holding_a_comment_end_does_not_leak(self, base, editor):
        store_path = next((base / "timeline").rglob("*.md"))
        with store_path.open("a", encoding="utf-8") as file:
            file.write("- 00:01 | odd --> entry\n")
        editor["write"] = "Mine."

        run_raw(input="1\n")

        content = store.latest_review(base).path.read_text(encoding="utf-8")
        assert "odd" not in content
        assert "Mine." in content

    def test_a_failed_request_keeps_the_text_and_comes_back(self, base, editor, monkeypatch):
        editor["write"] = "Kept through a failure."

        def fails(self, prompt, system_prompt=None, **kwargs):
            raise RuntimeError("no connection")

        monkeypatch.setattr(FakeClient, "generate", fails)

        result = run_raw(input="1\np\n")

        assert result.exit_code == 0, result.output
        review = store.latest_review(base)
        assert not review.is_done
        assert review.proposals_pending
        assert "Kept through a failure." in review.path.read_text(encoding="utf-8")

        monkeypatch.undo()


class TestWhenThereIsNothingToReflectOn:
    def test_carried_items_alone_do_not_ask_for_a_reflection(self, base):
        finish_with_deferred(base, 1)
        for path in (base / "timeline").rglob("*.md"):
            path.unlink()

        result = run_raw(input="3\n")

        assert result.exit_code == 0, result.output
        assert "Reflection" not in result.output
        assert store.latest_review(base).is_done


class TestAddingItems:
    @pytest.fixture
    def review(self, base):
        run_raw(input="p\n")
        return base

    def test_a_new_document(self, review):
        result = run_raw("add", "A topic", "--why", "reason", "--type", "판단", "--evidence", "2026-11-09")

        assert result.exit_code == 0, result.output
        item = store.latest_review(review).items[0]
        assert (item.kind, item.title, item.why, item.doc_type) == (store.KIND_NEW, "A topic", "reason", "판단")
        assert item.evidence == ["2026-11-09"]

    def test_an_open_question_in_an_existing_document(self, review):
        (review / "modules" / "news.md").write_text("# news\n", encoding="utf-8")

        result = run_raw("add", "Split it?", "--target", "news", "--heading", "열린 질문")

        assert result.exit_code == 0, result.output
        item = store.latest_review(review).items[0]
        assert (item.kind, item.target, item.heading) == (store.KIND_UPDATE, "news", "열린 질문")
        assert "news > 열린 질문" in store.item_label(item)

    def test_an_unknown_document_is_refused(self, review):
        result = run_raw("add", "A topic", "--target", "absent")

        assert result.exit_code == 1
        assert store.latest_review(review).items == []

    def test_a_heading_needs_a_document(self, review):
        assert run_raw("add", "A topic", "--heading", "열린 질문").exit_code == 1

    def test_no_review_yet(self, base):
        assert run_raw("add", "A topic").exit_code == 1

    def test_json_output(self, review):
        result = run_raw("add", "A topic", "--json")

        payload = json.loads(result.output.strip().splitlines()[-1])
        assert payload["ok"] is True
        assert payload["review"]["items"][0]["title"] == "A topic"

    def test_a_finished_review_passes_it_to_the_next_one(self, base):
        run(input="")
        assert store.latest_review(base).is_done

        run_raw("add", "Afterwards")
        add_entry_now(base)
        FakeClient.answer = answer(0)
        run(input="3\n")

        latest = store.latest_review(base)
        assert [item.title for item in latest.items] == ["Afterwards"]
        assert latest.items[0].carried

    def test_adding_during_the_item_menu(self, base):
        FakeClient.answer = answer(1)

        result = run(input="a\nBy hand\n\n3\n3\n")

        assert result.exit_code == 0, result.output
        assert sorted(item.title for item in store.latest_review(base).items) == ["By hand", "Topic 1"]

    def test_the_heading_reaches_the_writing_instructions(self, base):
        from memory_tool.review import writer

        (base / "modules" / "news.md").write_text("# news\n", encoding="utf-8")
        item = store.Item(number=1, kind=store.KIND_UPDATE, title="t", target="news", heading="열린 질문")

        assert "열린 질문" in writer._task_text(base, item)


class TestOldReviewFiles:
    OLD = """---
type: review
period_start: 2026-10-01T00:00
period_end: 2026-10-02T00:00
status: in_progress
entry_count: 1
active_days: 1
dropped: 0
reflection: written
items: []
---
# 리뷰

## 옮기기

제안한 항목이 없습니다.

## 돌아보기

예전에 쓴 글입니다.
"""

    def test_the_text_survives_and_stays_under_its_heading(self, base):
        path = base / "reviews" / "2026-10-02.md"
        path.parent.mkdir()
        path.write_text(self.OLD, encoding="utf-8")

        review = store.load_review(path)
        store.save_review(review)

        content = path.read_text(encoding="utf-8")
        assert "## 돌아보기\n\n예전에 쓴 글입니다." in content
        assert store.reflection_text(path) == "예전에 쓴 글입니다."
        assert not store.load_review(path).proposals_pending


class TestWhatTheReviewSays:
    def test_the_end_message_reports_the_reflection(self, base):
        FakeClient.answer = answer(0)

        output = " ".join(run(input="").output.split())

        assert ("Reflection: skipped" in output) or ("회고: 건너뜀" in output)

    def test_no_candidates_are_stated(self, base):
        FakeClient.answer = answer(0)

        output = " ".join(run(input="").output.split())

        assert ("Nothing in this period" in output) or ("문서로 남길 만한 내용이 없습니다" in output)

    def test_the_old_words_are_gone_from_a_new_file(self, base):
        run_raw(input="p\n")

        content = store.latest_review(base).path.read_text(encoding="utf-8")
        assert ("## To keep" in content) or ("## 남길 것" in content)
        assert ("## Reflection" in content) or ("## 회고" in content)
        assert "돌아보기" not in content and "옮기기" not in content


def test_inserting_and_removing_entries_leaves_the_file_as_it_was(tmp_path):
    path = tmp_path / "review.md"
    original = "# r\n\n## 회고\n\n<!-- 질문 -->\n\n내 글\n"
    path.write_text(original, encoding="utf-8")

    store.insert_entries(path, ["2026-01-01 09:00 | an entry"])
    assert "an entry" in path.read_text(encoding="utf-8")
    assert store.reflection_text(path) == "내 글"

    store.remove_entries(path)
    assert path.read_text(encoding="utf-8") == original
