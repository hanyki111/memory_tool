"""Tests for the recent decisions msummary adds to its prompt. All data is synthetic."""

from datetime import date

import pytest

from memory_tool.summary.context import ContextGatherer

MARCH = (date(2026, 3, 1), date(2026, 3, 31))


def judgment(modules, name, at, description="", title=None, doc_type="판단"):
    path = modules / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"type: {doc_type}\n"
        f"description: {description}\n"
        "generated:\n"
        "  by: human:tester\n"
        f"  at: {at}\n"
        "---\n\n"
        f"# {title or name}\n\n본문\n",
        encoding="utf-8",
    )


@pytest.fixture
def modules(tmp_path):
    folder = tmp_path / "modules"
    folder.mkdir()
    return folder


def recent(base, start=MARCH[0], end=MARCH[1]):
    return ContextGatherer(base)._get_recent_decisions(start, end)


def test_judgment_documents_made_in_the_period(modules):
    judgment(modules, "work/backup-method", "2026-03-05T10:00:00+09:00", "증분 백업으로 바꾼 이유", "백업 방식")
    judgment(modules, "work/old", "2026-02-27T10:00:00+09:00", "기간 밖")
    judgment(modules, "work/reference", "2026-03-06T10:00:00+09:00", "참고 문서", doc_type="참고")

    assert recent(modules.parent) == ["**2026-03-05**: 백업 방식: 증분 백업으로 바꾼 이유"]


def test_a_judgment_without_a_description_uses_its_title(modules):
    judgment(modules, "notes/port", "2026-03-07", title="포트 선택")

    assert recent(modules.parent) == ["**2026-03-07**: 포트 선택"]


def test_legacy_logs_in_nested_modules(modules):
    nested = modules / "project" / "api"
    nested.mkdir(parents=True)
    (nested / "decisions.md").write_text(
        "# Decisions\n\n### 2026-03-02: JWT 사용\n세션 대신\n\n### 2026-01-02: 오래된 결정\n", encoding="utf-8"
    )

    assert recent(modules.parent) == ["**2026-03-02**: JWT 사용\n세션 대신"]


def test_a_decisions_section_inside_a_document(modules):
    (modules / "design.md").write_text(
        "# Design\n\n본문\n\n# Decisions\n\n### 2026-03-09: 캐시 끄기\n", encoding="utf-8"
    )

    assert recent(modules.parent) == ["**2026-03-09**: 캐시 끄기"]


def test_the_five_most_recent_oldest_first(modules):
    for day in range(1, 8):
        judgment(modules, f"d{day}", f"2026-03-0{day}T09:00:00", f"결정 {day}")

    assert [line[:14] for line in recent(modules.parent)] == [
        "**2026-03-03**", "**2026-03-04**", "**2026-03-05**", "**2026-03-06**", "**2026-03-07**",
    ]


def test_archived_modules_and_broken_files_are_skipped(modules):
    judgment(modules, "archive/gone", "2026-03-05", "보관됨")
    (modules / "broken.md").write_bytes(b"\xff\xfe not utf-8")

    assert recent(modules.parent) == []


def test_no_modules_folder(tmp_path):
    assert recent(tmp_path) == []
