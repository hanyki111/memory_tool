"""Tests for review proposals and starting a review. All data is synthetic."""

import json
from datetime import datetime

import pytest

from memory_tool.core.writing_guides import read_guide_file
from memory_tool.review import proposer, session, store
from memory_tool.review.collector import Entry
from memory_tool.review.store import Item, ReviewError
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer

NOW = datetime(2026, 10, 10, 9, 0)


class FakeClient:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def generate(self, prompt, system_prompt=None, **kwargs):
        self.calls.append((prompt, system_prompt))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def answer(*proposals, more=0):
    return json.dumps({"proposals": list(proposals), "more": more}, ensure_ascii=False)


def new(title="백업 방식을 바꾼 이유", evidence=("2026-10-05",), **extra):
    return {"kind": "new", "title": title, "target": None, "type": "판단",
            "why": "결정의 근거", "evidence": list(evidence), **extra}


def update(target="server", title="포트 번호", evidence=("2026-10-05",)):
    return {"kind": "update", "title": title, "target": target, "type": "참고",
            "why": "값이 바뀜", "evidence": list(evidence)}


@pytest.fixture(autouse=True)
def base(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    monkeypatch.chdir(tmp_path)
    clear_cache()
    write_pointer(tmp_path, ".memory")
    folder = tmp_path / ".memory"
    (folder / "modules").mkdir(parents=True)
    (folder / "modules" / "server.md").write_text(
        "---\ndescription: 서버 설정 값\n---\n# server\n", encoding="utf-8"
    )
    (folder / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    day = folder / "timeline" / "daily" / "2026-10"
    day.mkdir(parents=True)
    (day / "2026-10-05.md").write_text("# T\n- 10:00 | 서버 포트를 8443으로 변경\n", encoding="utf-8")
    (day / "2026-10-06.md").write_text("# T\n- 11:00 | 증분 백업으로 변경\n", encoding="utf-8")
    clear_cache()
    yield folder
    clear_cache()


ENTRIES = [
    Entry(datetime(2026, 10, 5, 10, 0), "서버 포트를 8443으로 변경"),
    Entry(datetime(2026, 10, 6, 11, 0), "증분 백업으로 변경"),
]
DOCUMENTS = [("server", "서버 설정 값")]


class TestParsing:
    def parse(self, text, rejected=()):
        return proposer.parse_proposals(text, ENTRIES, DOCUMENTS, list(rejected))

    def test_reads_a_proposal(self):
        items, left_out = self.parse(answer(new(), more=2))

        assert items[0].title == "백업 방식을 바꾼 이유"
        assert items[0].doc_type == "판단"
        assert items[0].evidence == ["2026-10-05"]
        assert left_out == 2

    def test_reads_json_around_a_code_fence(self):
        items, _ = self.parse("Here you go:\n```json\n" + answer(new()) + "\n```\n")

        assert len(items) == 1

    @pytest.mark.parametrize("bad", ["no json here", "[1, 2]", '{"more": 1}', "{broken"])
    def test_refuses_an_answer_in_another_form(self, bad):
        with pytest.raises(ValueError):
            self.parse(bad)

    def test_drops_a_proposal_citing_a_day_without_entries(self):
        items, _ = self.parse(answer(new(evidence=("2026-10-05", "2026-01-01")), new(title="ok")))

        assert [item.title for item in items] == ["ok"]

    def test_drops_a_proposal_without_evidence(self):
        items, _ = self.parse(answer(new(evidence=())))

        assert items == []

    def test_drops_an_update_of_a_missing_document(self):
        items, _ = self.parse(answer(update(target="nowhere")))

        assert items == []

    @pytest.mark.parametrize("written", ["server", "server.md", "/server/", "server\\"])
    def test_accepts_spellings_of_a_known_document(self, written):
        items, _ = self.parse(answer(update(target=written)))

        assert items[0].target == "server"

    def test_drops_a_rejected_topic(self):
        items, _ = self.parse(answer(new()), rejected=["백업 방식을 바꾼 이유"])

        assert items == []

    def test_unknown_type_is_left_empty(self):
        items, _ = self.parse(answer(new(type="결정")))

        assert items[0].doc_type is None

    def test_updates_come_first_then_topics_seen_on_more_days(self):
        items, _ = self.parse(answer(
            new(title="one day"),
            new(title="two days", evidence=("2026-10-05", "2026-10-06")),
            update(),
        ))

        assert [item.title for item in items] == ["포트 번호", "two days", "one day"]

    def test_keeps_the_limit_and_counts_the_rest(self):
        items, left_out = self.parse(
            answer(*[new(title=f"t{n}") for n in range(7)], more=1)
        )

        assert len(items) == 5
        assert left_out == 3


class TestPrompt:
    def test_sends_paths_and_descriptions_but_not_bodies(self, base):
        (base / "modules" / "server.md").write_text(
            "---\ndescription: 서버 설정 값\n---\n# server\nSECRET BODY\n", encoding="utf-8"
        )
        client = FakeClient(answer())

        proposer.propose(base, ENTRIES, client)

        prompt, system = client.calls[0]
        assert "server: 서버 설정 값" in prompt
        assert "SECRET BODY" not in prompt
        assert "2026-10-05 10:00 | 서버 포트를 8443으로 변경" in prompt
        assert "리뷰 제안 기준" in system

    def test_users_guide_takes_precedence(self, base):
        (base / "guides").mkdir()
        (base / "guides" / "review-proposals.md").write_text("MY CRITERIA", encoding="utf-8")
        client = FakeClient(answer())

        proposer.propose(base, ENTRIES, client)

        assert "MY CRITERIA" in client.calls[0][1]

    def test_refuses_too_much_without_calling(self, base):
        client = FakeClient(answer())
        huge = [Entry(datetime(2026, 10, 5), "x" * (proposer.MAX_ENTRY_BYTES + 1))]

        with pytest.raises(ReviewError):
            proposer.propose(base, huge, client)

        assert client.calls == []

    def test_bundled_guide_exists(self):
        assert "리뷰 제안 기준" in read_guide_file(proposer.CRITERIA_GUIDE)


class TestSplitNote:
    def test_only_a_target_worth_splitting_gets_a_note(self, base):
        long_document = "".join(f"# Section {n}\n" + "line\n" * 70 for n in range(6))
        (base / "modules" / "long.md").write_text(long_document, encoding="utf-8")
        client = FakeClient(answer(update(target="long"), update(title="short one")))

        items, _ = proposer.propose(base, ENTRIES, client)

        notes = {item.target: item.split_note for item in items}
        assert notes["long"]["sections"] == 6
        assert notes["long"]["lines"] >= 300
        assert notes["server"] is None


class TestOpening:
    def test_starts_with_proposals_and_statistics(self, base):
        client = FakeClient(answer(update(), more=1))

        review = session.open_review(base, NOW, client=client)

        assert review.path.name == "2026-10-10.md"
        assert review.start == "2026-09-27T00:00"
        assert review.end == "2026-10-10T09:00"
        assert (review.entry_count, review.active_days, review.dropped) == (2, 2, 1)
        assert review.items[0].number == 1

    def test_resuming_keeps_the_review_without_calling(self, base):
        client = FakeClient(answer(new()))
        first = session.open_review(base, NOW, client=client)
        store.defer(first, 1)
        store.save_review(first)

        again = session.open_review(base, datetime(2026, 10, 20), client=client)

        assert len(client.calls) == 1
        assert again.path == first.path
        assert again.items[0].state == store.STATE_DEFERRED
        assert again.end == first.end

    @pytest.mark.parametrize(
        "failure",
        [RuntimeError("provider down"), "not json at all", '{"proposals": "many"}'],
    )
    def test_failure_writes_nothing_and_keeps_the_last_review(self, base, failure):
        previous = session.open_review(base, NOW, client=FakeClient(answer()))
        previous.status = store.STATUS_DONE
        store.save_review(previous)
        (base / "timeline" / "daily" / "2026-10" / "2026-10-11.md").write_text(
            "# T\n- 10:00 | 새 기록\n", encoding="utf-8"
        )

        with pytest.raises(ReviewError):
            session.open_review(base, datetime(2026, 10, 12), client=FakeClient(failure))

        assert store.review_files(base) == [previous.path]
        assert store.latest_review(base).end == previous.end

    def test_no_entries_and_no_open_items(self, base):
        client = FakeClient(answer())

        assert session.open_review(base, datetime(2027, 3, 1), client=client) is None
        assert client.calls == []
        assert store.review_files(base) == []

    def test_no_new_entries_but_open_items_skips_the_llm(self, base):
        first = session.open_review(base, NOW, client=FakeClient(answer(new())))
        store.defer(first, 1)
        first.status = store.STATUS_DONE
        store.save_review(first)
        client = FakeClient(answer())

        second = session.open_review(base, datetime(2026, 10, 15), client=client)

        assert client.calls == []
        assert second.items[0].carried

    def test_since_reaches_entries_before_the_first_window(self, base):
        client = FakeClient(answer())

        review = session.open_review(
            base, datetime(2026, 12, 1), since=datetime(2026, 10, 1), client=client
        )

        assert review.entry_count == 2

    def test_future_since_is_refused(self, base):
        with pytest.raises(ReviewError):
            session.open_review(base, NOW, since=datetime(2030, 1, 1), client=FakeClient(answer()))

    def test_choosing_creates_no_module_file(self, base):
        before = sorted(p.name for p in (base / "modules").rglob("*"))
        review = session.open_review(base, NOW, client=FakeClient(answer(new())))

        store.defer(review, 1)
        store.save_review(review)

        assert sorted(p.name for p in (base / "modules").rglob("*")) == before

    def test_fixed_questions_can_be_configured(self, base):
        (base / "config.yaml").write_text(
            "version: '1.0'\nreview:\n  reflection_questions:\n    - 무엇이 달라졌나요?\n",
            encoding="utf-8",
        )
        clear_cache()

        review = session.open_review(base, NOW, client=FakeClient(answer()))

        assert "<!-- 무엇이 달라졌나요? -->" in review.path.read_text(encoding="utf-8")
