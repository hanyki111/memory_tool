"""Tests for archiving a module that was consolidated into a single document.

`marchive` only knew the legacy layout: it opened decisions.md, current.md and
PLAN-*.md inside the module folder, so on a consolidated module it stopped at
"decisions.md not found". In one document those are sections, and archiving has
to cut a section without disturbing anything around it.

The fixtures follow modules found in use: em-dash rules between parts, a
Dependencies heading under the decisions title, entries at H2 in one project
and at H3 below framing headings in another, and "#35a" / "#35b" numbering.
"""

import pytest

from memory_tool.core.archiver import Archiver, ArchiverError
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def root(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    write_pointer(project, ".memory")
    base = project / ".memory"
    (base / "modules").mkdir(parents=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    return project


TEMPLATE_DOC = """# Module: sample

**Kind:** implementation

---

# Current Status: sample

## 1. Overview

Long status text.

## Related Files

- **Source:** `src/sample/`
———

# 기술 결정 (Decisions)

## Decision 1: First choice (2026-08-25,

confirmed 2026-08-26)

Context: why the first.

Status: Accepted

## Decision 2: Second choice (2026-08-26)

Context: why the second.

Status: Accepted

———

## Dependencies

- none

## 범위와 전제

Scope text.
"""

NUMBERED_DOC = """# Module: pm

---

# Key Decisions

> **Recent decisions**

---

## Writing Guidelines

Keep entries short.

---

## Recent Decisions

### #3: Newest (2026-03-01)

Body three.

---

### #2b: Later half (2026-02-20)

Body two b.

---

### #2a: Earlier half (2026-02-01)

Body two a.

---

### #1: Oldest (2026-01-01)

Body one.

---

# Dependencies

None yet
"""


def write_doc(root, name, content, layout="encapsulated", newline="\n"):
    modules = root / ".memory" / "modules"
    basename = name.split("/")[-1]
    if layout == "encapsulated":
        path = modules / name / f"{basename}.md"
    else:
        path = modules / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content.replace("\n", newline))
    return path


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def after(text, marker):
    return text[text.index(marker):]


class TestDecisionsSection:
    def test_archives_oldest_and_keeps_the_rest_of_the_document(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)

        archive_file, count = Archiver(root, "sample").archive_decisions_by_count(1)

        assert count == 1
        assert archive_file == doc.parent / "archive" / "decisions-1-1.md"

        archived = archive_file.read_text(encoding="utf-8")
        assert "## Decision 1: First choice (2026-08-25,\n\nconfirmed 2026-08-26)" in archived
        assert "Decision 2" not in archived

        text = read(doc)
        assert "Decision 1" not in text
        assert "## Decision 2: Second choice" in text
        assert "> For decisions #1-#1, see [archive/decisions-1-1.md](./archive/decisions-1-1.md)" in text

        # Everything outside the entries is byte-for-byte what it was.
        assert after(text, "———\n\n## Dependencies") == after(TEMPLATE_DOC, "———\n\n## Dependencies")
        assert text.split("# 기술 결정")[0] == TEMPLATE_DOC.split("# 기술 결정")[0]

    def test_backup_is_the_untouched_document(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)
        archiver = Archiver(root, "sample")

        archiver.archive_decisions_by_count(1)

        assert archiver.last_backup == doc.with_suffix(".md.bak")
        assert read(archiver.last_backup) == TEMPLATE_DOC

    def test_archiving_every_entry_keeps_the_following_part(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)

        Archiver(root, "sample").archive_decisions_by_count(0)

        text = read(doc)
        assert "## Decision" not in text
        assert "> For decisions #1-#2" in text
        assert after(text, "———\n\n## Dependencies") == after(TEMPLATE_DOC, "———\n\n## Dependencies")

    def test_h3_entries_under_framing_headings(self, root):
        doc = write_doc(root, "pm", NUMBERED_DOC)
        archiver = Archiver(root, "pm")

        labels = [d["entry"].label for d in archiver._load_decisions()]
        assert labels == ["3", "2b", "2a", "1"]

        archive_file, count = archiver.archive_decisions_by_count(2)

        # "#2b" is newer than "#2a" even though both are number 2.
        assert count == 2
        archived = archive_file.read_text(encoding="utf-8")
        assert archived.index("#1: Oldest") < archived.index("#2a: Earlier half")

        text = read(doc)
        assert "> For decisions #1-#2a" in text
        assert "## Writing Guidelines" in text
        assert "## Recent Decisions" in text
        assert "### #3: Newest" in text
        assert "### #2b: Later half" in text
        assert "#2a" not in text.split("> For decisions")[1].split("\n", 1)[1]
        assert text.endswith("---\n\n# Dependencies\n\nNone yet\n")

    def test_up_to_and_older_than(self, root):
        write_doc(root, "pm", NUMBERED_DOC)

        _, count = Archiver(root, "pm").archive_decisions_by_number(2, dry_run=True)
        assert count == 3

        _, count = Archiver(root, "pm").archive_decisions_by_date("1d", dry_run=True)
        assert count == 4

    def test_suggest_names_the_document(self, root):
        write_doc(root, "pm", NUMBERED_DOC)

        result = Archiver(root, "pm").suggest_archive(age_threshold_months=1)

        assert "pm.md (decisions section)" in result["summary"]
        assert result["archive_count"] == 4

    def test_dry_run_writes_nothing(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)

        archive_file, count = Archiver(root, "sample").archive_decisions_by_count(1, dry_run=True)

        assert count == 1
        assert not archive_file.exists()
        assert read(doc) == TEMPLATE_DOC
        assert not doc.with_suffix(".md.bak").exists()

    def test_flat_module_gets_its_own_archive_folder(self, root):
        doc = write_doc(root, "group/sample", TEMPLATE_DOC, layout="flat")

        archive_file, _ = Archiver(root, "group/sample").archive_decisions_by_count(1)

        assert archive_file == doc.parent / "sample" / "archive" / "decisions-1-1.md"
        assert "[sample/archive/decisions-1-1.md](./sample/archive/decisions-1-1.md)" in read(doc)

    def test_crlf_document_stays_crlf(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC, newline="\r\n")

        Archiver(root, "sample").archive_decisions_by_count(1)

        text = read(doc)
        assert "\r\n" in text
        assert "\n" not in text.replace("\r\n", "")

    def test_existing_archive_is_not_overwritten(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)
        existing = doc.parent / "archive" / "decisions-1-1.md"
        existing.parent.mkdir()
        existing.write_text("earlier archive", encoding="utf-8")

        with pytest.raises(ArchiverError, match="already exists"):
            Archiver(root, "sample").archive_decisions_by_count(1)

        assert existing.read_text(encoding="utf-8") == "earlier archive"
        assert read(doc) == TEMPLATE_DOC

    def test_several_decisions_sections_are_refused(self, root):
        merged = TEMPLATE_DOC + "\n# Other - Decisions\n\n## Decision 9: x (2026-01-01)\n"
        doc = write_doc(root, "sample", merged)

        with pytest.raises(ArchiverError, match="2 decisions sections found"):
            Archiver(root, "sample").archive_decisions_by_count(0)

        assert read(doc) == merged

    def test_section_without_numbered_entries(self, root):
        write_doc(root, "sample", "# Module: s\n\n# Decisions\n\n## Notes\n\nfree text\n")

        with pytest.raises(ArchiverError, match="No numbered decisions"):
            Archiver(root, "sample").archive_decisions_by_count(0)

    def test_headings_inside_fences_are_ignored(self, root):
        doc_text = TEMPLATE_DOC.replace(
            "Context: why the second.",
            "Context: why the second.\n\n```bash\n# Decisions\n## Decision 7: not real\n```",
        )
        write_doc(root, "sample", doc_text)

        labels = [d["entry"].label for d in Archiver(root, "sample")._load_decisions()]

        assert labels == ["1", "2"]


class TestCurrentSection:
    def test_resets_status_and_keeps_related_files(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)

        archive_file = Archiver(root, "sample").archive_current(3)

        assert archive_file == doc.parent / "archive" / "current-phase3.md"
        archived = archive_file.read_text(encoding="utf-8")
        assert archived.startswith("# Current Status: sample")
        assert "Long status text." in archived

        text = read(doc)
        current = text.split("# Current Status: sample")[1].split("# 기술 결정")[0]
        assert "Long status text." not in current
        assert "> **Phase 4 in progress**" in current
        assert "[archive/current-phase3.md](./archive/current-phase3.md)" in current
        assert "### In Progress" in current
        assert "## Related Files\n\n- **Source:** `src/sample/`\n———\n\n" in current
        assert after(text, "# 기술 결정") == after(TEMPLATE_DOC, "# 기술 결정")

    def test_missing_current_section(self, root):
        write_doc(root, "sample", "# Module: s\n\nbody\n")

        with pytest.raises(ArchiverError, match="current status"):
            Archiver(root, "sample").archive_current(1)


class TestPlans:
    def test_plan_files_in_an_encapsulated_module_still_move(self, root):
        doc = write_doc(root, "sample", TEMPLATE_DOC)
        (doc.parent / "PLAN-x.md").write_text("plan", encoding="utf-8")

        moved = Archiver(root, "sample").archive_plans()

        assert moved == [doc.parent / "archive" / "plans" / "PLAN-x.md"]

    def test_flat_module_does_not_take_its_siblings_plans(self, root):
        doc = write_doc(root, "group/sample", TEMPLATE_DOC, layout="flat")
        (doc.parent / "PLAN-x.md").write_text("plan", encoding="utf-8")

        assert Archiver(root, "group/sample").archive_plans() == []
        assert (doc.parent / "PLAN-x.md").exists()

    def test_plan_modules_are_listed(self, root):
        write_doc(root, "sample", TEMPLATE_DOC)
        write_doc(root, "PLAN-start", "# Intent: PLAN-start\n\n**Kind:** intent | **Nature:** plan\n")
        write_doc(root, "roadmap", "# Intent: roadmap\n\n**Kind:** intent | **Nature:** plan\n")

        assert Archiver(root, "sample").plan_modules() == ["PLAN-start", "roadmap"]


class TestLegacyLayout:
    def test_decisions_md_is_still_rebuilt(self, root):
        module = root / ".memory" / "modules" / "old"
        module.mkdir(parents=True)
        (module / "current.md").write_text("# Current Status\n", encoding="utf-8")
        (module / "decisions.md").write_text(
            "# Key Decisions\n\n"
            "### 2026-01-01: First\n\n**결정 #1:** one\n\n---\n\n"
            "### 2026-01-02: Second\n\n**결정 #2:** two\n\n---\n",
            encoding="utf-8",
        )

        archiver = Archiver(root, "old")
        archive_file, count = archiver.archive_decisions_by_count(1)

        assert archiver.module_doc is None
        assert count == 1
        assert archive_file == module / "archive" / "decisions-1-1.md"
        assert archiver.last_backup == module / "decisions.md.bak"
        rebuilt = (module / "decisions.md").read_text(encoding="utf-8")
        assert "Second" in rebuilt and "First" not in rebuilt
