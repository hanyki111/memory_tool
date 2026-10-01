"""Tests for reading a module that was consolidated into a single document.

`mcheck` reported every consolidated module as having no Related Files at all.
Two causes sat behind that: the lookup opened a fixed `current.md`, which a
consolidated module no longer has, and the checker named `a/b/b.md` as the
module `a/b/b`, so its warnings pointed at paths that never existed.
"""

import pytest

from memory_tool.context.related_files import (
    RelatedFilesParser,
    get_module_related_files,
    resolve_module_document,
)
from memory_tool.utils.path_checker import PathChecker
from memory_tool.utils.paths import ENV_BASE, ENV_ROOT, clear_cache, write_pointer


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


def make_base(root):
    root.mkdir(parents=True, exist_ok=True)
    write_pointer(root, ".memory")
    base = root / ".memory"
    (base / "modules").mkdir(parents=True, exist_ok=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    clear_cache()
    return base


STANDARD_DOC = """# Module: sample

## Related Files

- **Source:** `src/sample/`
- **Tests:** `tests/sample/`

## Overview

Anything at all.
"""


def write_module(base, name, content=STANDARD_DOC, layout="encapsulated"):
    """Create a module document in one of the three layouts in use."""
    modules = base / "modules"
    basename = name.split("/")[-1]

    if layout == "encapsulated":
        path = modules / name / f"{basename}.md"
    elif layout == "flat":
        path = modules / f"{name}.md"
    elif layout == "legacy":
        path = modules / name / "current.md"
    else:
        raise ValueError(layout)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def make_referenced_paths(root):
    (root / "src" / "sample").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "sample").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Document resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layout", ["encapsulated", "flat", "legacy"])
def test_related_files_read_from_every_layout(tmp_path, layout):
    """All three layouts hold a module document, and all three must be read."""
    base = make_base(tmp_path)
    doc = write_module(base, "sample", layout=layout)

    related = get_module_related_files(doc.parent if layout != "flat" else doc)

    assert related.format_type == "standard"
    assert related.source == ["src/sample/"]
    assert related.tests == ["tests/sample/"]


def test_document_itself_may_be_passed(tmp_path):
    """Callers that already resolved the document should not have to undo it."""
    base = make_base(tmp_path)
    doc = write_module(base, "sample")

    assert resolve_module_document(doc) == doc
    assert get_module_related_files(doc).source == ["src/sample/"]


def test_missing_module_yields_no_paths(tmp_path):
    base = make_base(tmp_path)

    related = get_module_related_files(base / "modules" / "absent")

    assert related.format_type == "none"
    assert related.is_empty()


# ---------------------------------------------------------------------------
# Consolidated documents carry more than one section
# ---------------------------------------------------------------------------


def test_every_standard_section_is_collected():
    """Consolidation concatenates the sections the former files each carried."""
    content = """# Module: merged

## Related Files

- **Source:** `first/`

## Notes

Text in between.

## Related Files

- **Tests:** `second/`
"""
    related = RelatedFilesParser().parse(content)

    assert related.source == ["first/"]
    assert related.tests == ["second/"]


def test_every_legacy_block_is_collected():
    content = """# Module: merged

### Feature one

**Key Files:**
- `one.py`

### Feature two

**Key Files:**
- `two.py`
"""
    related = RelatedFilesParser().parse(content)

    assert related.format_type == "legacy"
    assert related.source == ["one.py", "two.py"]


def test_repeated_path_recorded_once():
    """The same file listed under two merged features is still one path."""
    content = """# Module: merged

**Key Files:**
- `shared.py`

### Later

**Key Files:**
- `shared.py`
"""
    related = RelatedFilesParser().parse(content)

    assert related.source == ["shared.py"]
    assert related.get_line_number("shared.py") == 4


# ---------------------------------------------------------------------------
# mcheck
# ---------------------------------------------------------------------------


def test_check_names_module_after_its_folder(tmp_path):
    """`a/b/b.md` is the module `a/b`; repeating the folder broke every path."""
    base = make_base(tmp_path)
    write_module(base, "project/feature")
    make_referenced_paths(tmp_path)

    summary = PathChecker(tmp_path).check_all_modules()

    assert [r.module_name for r in summary.results] == ["project/feature"]
    assert summary.total_valid == 2
    assert summary.total_missing == 0


def test_check_finds_paths_in_consolidated_module(tmp_path):
    """The regression itself: a consolidated module reported nothing at all."""
    base = make_base(tmp_path)
    write_module(base, "feature")
    make_referenced_paths(tmp_path)

    result = PathChecker(tmp_path).check_module("feature")

    assert result.has_related_files
    assert result.total_count == 2
    assert not result.has_issues


def test_warning_points_at_the_document_that_was_read(tmp_path):
    """A consolidated module has no current.md to send the reader to."""
    base = make_base(tmp_path)
    doc = write_module(base, "feature", content="# Module: feature\n\nNo paths.\n")

    result = PathChecker(tmp_path).check_module("feature")

    assert not result.has_related_files
    assert result.doc_path == doc
    assert result.source_file.endswith("modules/feature/feature.md")


def test_missing_path_error_points_at_its_line(tmp_path):
    base = make_base(tmp_path)
    write_module(base, "feature")

    result = PathChecker(tmp_path).check_module("feature")
    errors = [r.format_error() for r in result.path_results if not r.exists]

    assert len(errors) == 2
    assert errors[0].endswith("modules/feature/feature.md:5: error: 'src/sample/' not found")


def test_archived_modules_excluded_unless_requested(tmp_path):
    base = make_base(tmp_path)
    write_module(base, "feature")
    write_module(base, "archive/retired")
    make_referenced_paths(tmp_path)

    checker = PathChecker(tmp_path)

    assert [r.module_name for r in checker.check_all_modules().results] == ["feature"]

    with_archive = checker.check_all_modules(include_archived=True)
    assert [r.module_name for r in with_archive.results] == [
        "archive/retired",
        "feature",
    ]
