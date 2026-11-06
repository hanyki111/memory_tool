"""Tests for review files, their rules, and gathering entries."""

from datetime import datetime

import pytest

from memory_tool.review import collector, store
from memory_tool.review.store import Item, ReviewError


def proposals(count, start=1):
    return [Item(number=0, kind=store.KIND_NEW, title=f"Topic {n}") for n in range(start, start + count)]


def begin(base, count=0, day="2026-10-01", **kwargs):
    return store.start_review(base, day, f"{day}T00:00", f"{day}T12:00", proposals(count), **kwargs)


def finish(review):
    review.status = store.STATUS_DONE
    store.save_review(review)


def write_day(base, month, name, lines):
    folder = base / "timeline" / "daily" / month
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("# Timeline\n" + "".join(f"{line}\n" for line in lines), encoding="utf-8")


class TestLimit:
    def test_refuses_to_defer_above_the_limit_and_allows_at_it(self, tmp_path):
        review = begin(tmp_path, 7)

        with pytest.raises(ReviewError):
            store.defer(review, 1)

        store.reject(review, 1)
        with pytest.raises(ReviewError):
            store.defer(review, 2)

        store.reject(review, 2)
        assert store.defer(review, 3).state == store.STATE_DEFERRED

    def test_item_being_written_still_counts(self, tmp_path):
        review = begin(tmp_path, 6)
        store.start_writing(review, 1)

        with pytest.raises(ReviewError):
            store.defer(review, 2)

        store.mark_written(review, 1)
        assert store.defer(review, 2).state == store.STATE_DEFERRED

    def test_open_items_never_exceed_the_limit_after_choosing(self, tmp_path):
        review = begin(tmp_path, 5)
        for number in range(1, 6):
            store.defer(review, number)
        finish(review)

        next_review = begin(tmp_path, 5, day="2026-10-08")
        assert len(next_review.open_items()) == 10

        for item in list(next_review.items):
            if next_review.can_defer():
                store.defer(next_review, item.number)
            else:
                store.reject(next_review, item.number)

        assert len(next_review.open_items()) == 5

    def test_settled_item_cannot_change(self, tmp_path):
        review = begin(tmp_path, 1)
        store.reject(review, 1)

        with pytest.raises(ReviewError):
            store.defer(review, 1)


class TestSettling:
    def test_waits_for_undecided_and_writing_items(self, tmp_path):
        review = begin(tmp_path, 2)
        assert not review.choices_settled()

        store.defer(review, 1)
        store.start_writing(review, 2)
        assert not review.choices_settled()

        store.mark_written(review, 2)
        assert review.choices_settled()

    def test_items_being_written_come_first(self, tmp_path):
        review = begin(tmp_path, 3)
        store.start_writing(review, 3)

        assert [item.number for item in review.undecided_items()] == [3, 1, 2]


class TestFiles:
    def test_round_trip(self, tmp_path):
        item = Item(
            number=0, kind=store.KIND_UPDATE, title="포트", target="server/config",
            doc_type="참고", why="값이 바뀜", evidence=["2026-10-05"],
            split_note={"lines": 840, "sections": 12},
        )
        review = store.start_review(
            tmp_path, "2026-10-08", "2026-10-01T00:00", "2026-10-08T09:30", [item],
            dropped=2, entry_count=42, active_days=7,
        )

        loaded = store.load_review(review.path)

        assert loaded.start == "2026-10-01T00:00"
        assert loaded.end == "2026-10-08T09:30"
        assert (loaded.dropped, loaded.entry_count, loaded.active_days) == (2, 42, 7)
        assert loaded.items[0].evidence == ["2026-10-05"]
        assert loaded.items[0].split_note == {"lines": 840, "sections": 12}
        assert loaded.items[0].number == 1

    def test_keeps_the_reflection_text(self, tmp_path):
        review = begin(tmp_path, 1, reflection_comment="<!-- question -->")
        text = review.path.read_text(encoding="utf-8")
        assert "<!-- question -->" in text

        review.path.write_text(text + "\nMy own words.\n\n### More\n", encoding="utf-8")
        store.reject(review, 1)
        store.save_review(review)

        saved = review.path.read_text(encoding="utf-8")
        assert "My own words." in saved
        assert "### More" in saved
        assert saved.count("<!-- question -->") == 1

    def test_summary_reflects_the_record(self, tmp_path):
        review = begin(tmp_path, 1)
        store.reject(review, 1)
        store.save_review(review)

        assert "Topic 1" in review.path.read_text(encoding="utf-8")
        assert store.load_review(review.path).items[0].state == store.STATE_REJECTED

    def test_second_review_of_a_day_gets_its_own_file(self, tmp_path):
        finish(begin(tmp_path))
        second = begin(tmp_path)

        assert second.path.name == "2026-10-01-2.md"
        assert store.latest_review(tmp_path).path == second.path

    def test_tenth_review_of_a_day_sorts_last(self, tmp_path):
        folder = store.reviews_folder(tmp_path)
        folder.mkdir()
        for name in ("2026-10-01.md", "2026-10-01-2.md", "2026-10-01-10.md"):
            (folder / name).write_text("", encoding="utf-8")

        assert store.review_files(tmp_path)[-1].name == "2026-10-01-10.md"

    def test_old_weekly_and_monthly_files_are_not_reviews(self, tmp_path):
        for relative in ("weekly/2025/W47.md", "monthly/2025/11.md", "templates/weekly.md"):
            path = store.reviews_folder(tmp_path) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# old\n", encoding="utf-8")

        assert store.latest_review(tmp_path) is None

    def test_unreadable_record_is_reported(self, tmp_path):
        folder = store.reviews_folder(tmp_path)
        folder.mkdir()
        (folder / "2026-10-01.md").write_text("# no frontmatter\n", encoding="utf-8")

        with pytest.raises(ReviewError):
            store.latest_review(tmp_path)


class TestCarrying:
    def test_open_items_come_first_and_old_file_lets_go(self, tmp_path):
        first = begin(tmp_path, 3)
        store.defer(first, 1)
        store.start_writing(first, 2)
        store.reject(first, 3)
        finish(first)

        second = begin(tmp_path, 1, day="2026-10-08")

        assert [item.title for item in second.items] == ["Topic 1", "Topic 2", "Topic 1"]
        assert [item.number for item in second.items] == [1, 2, 3]
        assert [item.carried for item in second.items] == [True, True, False]
        assert not any(item.decided for item in second.items)
        assert second.items[1].state == store.STATE_WRITING

        old = store.load_review(first.path)
        assert [item.state for item in old.items] == [
            store.STATE_CARRIED, store.STATE_CARRIED, store.STATE_REJECTED,
        ]

    def test_refuses_to_start_during_a_review(self, tmp_path):
        begin(tmp_path, 1)

        with pytest.raises(ReviewError):
            begin(tmp_path, 1, day="2026-10-08")

        assert len(store.review_files(tmp_path)) == 1

    def test_rejected_titles(self, tmp_path):
        first = begin(tmp_path, 2)
        store.reject(first, 1)
        store.defer(first, 2)
        finish(first)

        assert store.rejected_titles(tmp_path) == ["Topic 1"]


class TestCollector:
    def test_reads_both_file_layouts(self, tmp_path):
        write_day(tmp_path, "2026-09", "2026-09-03.md", ["- 10:00 | dated name"])
        write_day(tmp_path, "2026-09", "04.md", ["- 11:00 | day name"])

        entries = collector.collect_entries(
            tmp_path, datetime(2026, 9, 1), datetime(2026, 9, 30, 23, 59)
        )

        assert [entry.text for entry in entries] == ["dated name", "day name"]
        assert collector.entry_statistics(entries) == (2, 2)

    def test_later_entries_of_a_review_day_reach_the_next_review(self, tmp_path):
        write_day(tmp_path, "2026-09", "2026-09-03.md", [
            "- 09:00 | before", "- 15:00 | after",
        ])
        start, end = collector.review_window("2026-09-03T12:00", datetime(2026, 9, 4, 8, 0))

        entries = collector.collect_entries(tmp_path, start, end)

        assert [entry.text for entry in entries] == ["after"]

    def test_entries_during_a_paused_review_reach_the_next_one(self, tmp_path):
        write_day(tmp_path, "2026-09", "2026-09-03.md", ["- 09:00 | in"])
        write_day(tmp_path, "2026-09", "2026-09-05.md", ["- 09:00 | during pause"])

        covered = collector.collect_entries(
            tmp_path, datetime(2026, 9, 1), datetime(2026, 9, 3, 12, 0)
        )
        start, end = collector.review_window("2026-09-03T12:00", datetime(2026, 9, 6))
        following = collector.collect_entries(tmp_path, start, end)

        assert [entry.text for entry in covered] == ["in"]
        assert [entry.text for entry in following] == ["during pause"]

    def test_first_review_reads_fourteen_days(self):
        start, end = collector.review_window(None, datetime(2026, 9, 30, 10, 5, 30))

        assert start == datetime(2026, 9, 17, 0, 0)
        assert end == datetime(2026, 9, 30, 10, 5)

    def test_since_overrides_the_last_review(self):
        start, _ = collector.review_window(
            "2026-09-20T12:00", datetime(2026, 9, 30), since=datetime(2026, 1, 1)
        )

        assert start == datetime(2026, 1, 1)

    def test_ignores_lines_that_are_not_entries(self, tmp_path):
        write_day(tmp_path, "2026-09", "2026-09-03.md", [
            "plain text", "- not an entry", "- 99:00 | bad time", "- 10:00 | good",
        ])

        entries = collector.collect_entries(
            tmp_path, datetime(2026, 9, 3), datetime(2026, 9, 3, 23, 59)
        )

        assert [entry.text for entry in entries] == ["good"]
