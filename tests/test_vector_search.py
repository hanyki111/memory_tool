"""Tests for semantic search over the timeline, with a fake embedding model.

All data is synthetic. The real model is never loaded.
"""

from pathlib import Path

import pytest

from memory_tool.core.vector_search import EmbeddingCache, VectorSearcher

WORDS = ["백업", "포트", "회의"]


class Vector(list):
    def tolist(self):
        return list(self)


class FakeModel:
    """Embeds a text by which of a few words it contains."""

    encoded = 0

    def encode(self, texts, convert_to_tensor=False, show_progress_bar=False):
        if isinstance(texts, str):
            return self._one(texts)
        return [self._one(text) for text in texts]

    def _one(self, text):
        FakeModel.encoded += 1
        return Vector([1.0 if word in text else 0.0 for word in WORDS] + [0.01])


def searcher(base: Path) -> VectorSearcher:
    """A searcher over ``base`` that does not load sentence-transformers."""
    found = VectorSearcher.__new__(VectorSearcher)
    found.base_path = base
    found.timeline_path = base / "timeline"
    found.cache_dir = base / ".embeddings"
    found.model = FakeModel()
    found.cache = EmbeddingCache(found.cache_dir)
    return found


def write(base: Path, relative: str, body: str) -> Path:
    path = base / "timeline" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Timeline\n{body}", encoding="utf-8")
    return path


@pytest.fixture
def base(tmp_path):
    FakeModel.encoded = 0
    write(tmp_path, "daily/2026-03/2026-03-01.md", "- 10:00 | 백업 방식을 바꿈\n")
    write(tmp_path, "daily/2026-03/02.md", "- 11:00 | 포트를 8443으로 바꿈\n")
    write(tmp_path, "2026-02/27.md", "- 09:00 | 백업 용량 점검\n")
    return tmp_path


def contents(results):
    return sorted(result["content"] for result in results)


class TestSearchReadsEveryFile:
    def test_second_search_still_finds_unchanged_files(self, base):
        first = searcher(base).semantic_search("백업", threshold=0.5)
        second = searcher(base).semantic_search("백업", threshold=0.5)

        assert contents(first) == ["백업 방식을 바꿈", "백업 용량 점검"]
        assert contents(second) == contents(first)

    def test_files_indexed_beforehand_are_still_searched(self, base):
        searcher(base).preindex_timeline()

        assert contents(searcher(base).semantic_search("포트", threshold=0.5)) == ["포트를 8443으로 바꿈"]

    def test_entries_are_embedded_only_once(self, base):
        searcher(base).semantic_search("백업", threshold=0.5)
        after_first = FakeModel.encoded

        searcher(base).semantic_search("백업", threshold=0.5)

        # The query is cached too, so nothing is embedded again.
        assert FakeModel.encoded == after_first

    def test_dates_for_every_layout(self, base):
        results = searcher(base).semantic_search("백업 포트", threshold=0.1, top_k=10)

        assert sorted((result["date"], result["line"]) for result in results) == [
            ("2026-02-27", 2),
            ("2026-03-01", 2),
            ("2026-03-02", 2),
        ]


class TestPreindex:
    def test_skips_unchanged_files_unless_forced(self, base):
        assert searcher(base).preindex_timeline()["files_processed"] == 3
        assert searcher(base).preindex_timeline()["files_processed"] == 0
        assert searcher(base).preindex_timeline(force=True)["files_processed"] == 3

    def test_a_changed_file_is_indexed_again(self, base):
        searcher(base).preindex_timeline()
        path = write(base, "daily/2026-03/02.md", "- 11:00 | 포트를 8443으로 바꿈\n- 12:00 | 회의\n")
        import os
        os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 10))

        assert searcher(base).preindex_timeline()["files_processed"] == 1

    def test_a_failed_embedding_leaves_files_unmarked(self, base):
        broken = searcher(base)

        def fail(*args, **kwargs):
            raise RuntimeError("model failed")

        broken.model.encode = fail
        with pytest.raises(RuntimeError):
            broken.preindex_timeline()

        assert searcher(base).preindex_timeline()["files_processed"] == 3
