"""Tests for base folder renaming (memory_tool.core.rebase).

The dangerous case is a base of ".", where the knowledge base shares a directory
with unrelated project files. Those tests are the important ones: a rename must
move knowledge-base content and nothing else.
"""

import pytest

from memory_tool.core.rebase import RebaseError, Rebaser
from memory_tool.utils.paths import (
    ENV_BASE,
    ENV_ROOT,
    ROOT_BASE,
    clear_cache,
    read_pointer,
    write_pointer,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.delenv(ENV_BASE, raising=False)
    clear_cache()
    yield
    clear_cache()


MODULE_MD = """# mod-a

## Related Files
- **Source:** `{base}/modules/mod-a/`
- **Docs:** `{base}/docs/guide.md`

## History
Decided in 2025-11 to keep everything under {base}/ for tidiness.
"""


def make_project(root, base_name, with_project_files=True, legacy=False):
    """Build a realistic project: knowledge base plus surrounding project files."""
    root.mkdir(parents=True, exist_ok=True)

    if legacy:
        base = root / ".memory"
        base_name = ".memory"
    else:
        write_pointer(root, base_name)
        base = root if base_name == ROOT_BASE else root / base_name

    for sub in ("timeline", "modules", "concepts"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (base / "config.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (base / "timeline" / "entry.md").write_text("- 10:00 | hello", encoding="utf-8")
    (base / ".connections.db").write_text("x", encoding="utf-8")
    (base / ".embeddings").mkdir(exist_ok=True)
    (base / ".embeddings" / "index.json").write_text("{}", encoding="utf-8")

    mod = base / "modules" / "mod-a"
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "mod-a.md").write_text(MODULE_MD.format(base=base_name), encoding="utf-8")

    if with_project_files:
        (root / "src").mkdir(exist_ok=True)
        (root / "src" / "app.py").write_text("print('app')", encoding="utf-8")
        (root / "README.md").write_text("project readme", encoding="utf-8")
        (root / "pyproject.toml").write_text("[project]", encoding="utf-8")
        (root / "venv").mkdir(exist_ok=True)
        (root / "venv" / "junk.md").write_text("noise", encoding="utf-8")

    clear_cache()
    return base


# ---------------------------------------------------------------------------
# subfolder -> subfolder
# ---------------------------------------------------------------------------


def test_rename_subfolder_moves_whole_directory(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)

    plan = rebaser.plan("memory")
    assert plan.ok
    rebaser.apply(plan)

    assert not (tmp_path / ".memory").exists()
    assert (tmp_path / "memory" / "timeline" / "entry.md").is_file()
    assert read_pointer(tmp_path) == "memory"


def test_rename_carries_hidden_state_files(tmp_path):
    """Caches and indexes live in the base folder and must not be left behind."""
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("memory"))

    assert (tmp_path / "memory" / ".connections.db").is_file()
    assert (tmp_path / "memory" / ".embeddings" / "index.json").is_file()


def test_rename_to_existing_nonempty_dir_is_refused(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "precious.md").write_text("do not clobber", encoding="utf-8")

    plan = Rebaser(tmp_path).plan("memory")

    assert not plan.ok
    assert (tmp_path / "memory" / "precious.md").read_text(encoding="utf-8") == "do not clobber"


def test_rename_to_empty_existing_dir_is_allowed(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    (tmp_path / "memory").mkdir()

    plan = Rebaser(tmp_path).plan("memory")

    assert plan.ok


def test_rename_to_same_name_is_refused(tmp_path):
    make_project(tmp_path, "memory")
    plan = Rebaser(tmp_path).plan("memory")

    assert not plan.ok
    assert "already" in " ".join(plan.errors).lower()


def test_rename_reserved_name_raises(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)

    with pytest.raises(RebaseError):
        Rebaser(tmp_path).plan("venv")


def test_rename_traversal_name_raises(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)

    with pytest.raises(RebaseError):
        Rebaser(tmp_path).plan("../escape")


def test_rename_uninitialized_project_is_refused(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    write_pointer(tmp_path, "memory")  # pointer but no folder
    clear_cache()

    plan = Rebaser(tmp_path).plan("other")

    assert not plan.ok


# ---------------------------------------------------------------------------
# subfolder -> project root  (the Obsidian vault case)
# ---------------------------------------------------------------------------


def test_move_to_root_places_content_at_top_level(tmp_path):
    make_project(tmp_path, "memory")
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan(ROOT_BASE))

    assert (tmp_path / "timeline" / "entry.md").is_file()
    assert (tmp_path / "modules" / "mod-a" / "mod-a.md").is_file()
    assert (tmp_path / "config.yaml").is_file()
    assert not (tmp_path / "memory").exists()
    assert read_pointer(tmp_path) == ROOT_BASE


def test_move_to_root_leaves_project_files_untouched(tmp_path):
    """The critical guarantee: a rename is not a directory merge."""
    make_project(tmp_path, "memory")
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan(ROOT_BASE))

    assert (tmp_path / "src" / "app.py").read_text(encoding="utf-8") == "print('app')"
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "project readme"
    assert (tmp_path / "pyproject.toml").is_file()
    assert (tmp_path / "venv" / "junk.md").is_file()


def test_move_to_root_refuses_on_name_collision(tmp_path):
    """A pre-existing ./timeline would otherwise be silently merged into."""
    make_project(tmp_path, "memory")
    (tmp_path / "timeline").mkdir()

    plan = Rebaser(tmp_path).plan(ROOT_BASE)

    assert not plan.ok
    assert "timeline" in " ".join(plan.errors)


def test_move_to_root_does_not_move_unknown_base_entries(tmp_path):
    """Unrecognized files inside the base stay put rather than landing in root."""
    base = make_project(tmp_path, "memory")
    (base / "scratch.txt").write_text("stray", encoding="utf-8")

    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan(ROOT_BASE))

    assert not (tmp_path / "scratch.txt").exists()
    assert (tmp_path / "memory" / "scratch.txt").is_file()


# ---------------------------------------------------------------------------
# project root -> subfolder
# ---------------------------------------------------------------------------


def test_move_from_root_collects_only_known_entries(tmp_path):
    make_project(tmp_path, ROOT_BASE)
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("knowledge"))

    assert (tmp_path / "knowledge" / "timeline" / "entry.md").is_file()
    assert (tmp_path / "knowledge" / "config.yaml").is_file()
    # unrelated project files must remain at the root
    assert (tmp_path / "src" / "app.py").is_file()
    assert (tmp_path / "README.md").is_file()
    assert not (tmp_path / "knowledge" / "src").exists()
    assert not (tmp_path / "knowledge" / "README.md").exists()


def test_move_from_root_skips_reference_rewriting(tmp_path):
    """Root-base paths have no prefix, so there is nothing safe to rewrite."""
    make_project(tmp_path, ROOT_BASE)
    plan = Rebaser(tmp_path).plan("knowledge")

    assert plan.rewrites == []
    assert any("no folder prefix" in w for w in plan.warnings)


# ---------------------------------------------------------------------------
# Reference rewriting
# ---------------------------------------------------------------------------


def test_default_rewrite_touches_only_related_files_section(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("memory"))

    text = (tmp_path / "memory" / "modules" / "mod-a" / "mod-a.md").read_text(
        encoding="utf-8"
    )

    assert "`memory/modules/mod-a/`" in text
    assert "`memory/docs/guide.md`" in text
    # The History prose keeps its historical wording
    assert "under .memory/ for tidiness" in text


def test_rewrite_all_also_rewrites_prose(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("memory", rewrite_all=True))

    text = (tmp_path / "memory" / "modules" / "mod-a" / "mod-a.md").read_text(
        encoding="utf-8"
    )

    assert "under memory/ for tidiness" in text
    assert ".memory/" not in text


def test_no_rewrite_leaves_all_references_alone(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("memory", rewrite=False))

    text = (tmp_path / "memory" / "modules" / "mod-a" / "mod-a.md").read_text(
        encoding="utf-8"
    )

    assert "`.memory/modules/mod-a/`" in text


def test_rewrite_to_root_base_strips_the_prefix(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan(ROOT_BASE))

    text = (tmp_path / "modules" / "mod-a" / "mod-a.md").read_text(encoding="utf-8")

    assert "`modules/mod-a/`" in text
    assert "`docs/guide.md`" in text


def test_rewrite_all_includes_root_docs(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    (tmp_path / "CLAUDE.md").write_text("Read .memory/docs/USAGE.md first.", encoding="utf-8")

    rebaser = Rebaser(tmp_path)
    plan = rebaser.plan("memory", rewrite_all=True)
    rebaser.apply(plan)

    assert "memory/docs/USAGE.md" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# .gitignore handling
# ---------------------------------------------------------------------------


def test_gitignore_entry_is_renamed_to_stay_ignored(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    (tmp_path / ".gitignore").write_text("# Memory\n.memory/\nvenv/\n", encoding="utf-8")

    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("memory"))

    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "memory/" in text
    assert ".memory/" not in text
    assert "venv/" in text


def test_gitignore_entry_is_commented_when_moving_to_root(tmp_path):
    """The root cannot ignore itself, so the rule is disabled and flagged."""
    make_project(tmp_path, "memory")
    (tmp_path / ".gitignore").write_text("memory/\n", encoding="utf-8")

    rebaser = Rebaser(tmp_path)
    plan = rebaser.plan(ROOT_BASE)
    rebaser.apply(plan)

    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert text.strip().startswith("#")
    assert any("visible to git" in w for w in plan.warnings)


def test_no_git_update_leaves_gitignore_alone(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    (tmp_path / ".gitignore").write_text(".memory/\n", encoding="utf-8")

    rebaser = Rebaser(tmp_path)
    rebaser.apply(rebaser.plan("memory", update_git=False))

    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == ".memory/\n"


def test_missing_gitignore_is_not_an_error(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    rebaser = Rebaser(tmp_path)
    plan = rebaser.plan("memory")

    assert plan.gitignore_edit is None
    assert plan.ok


# ---------------------------------------------------------------------------
# Plan integrity
# ---------------------------------------------------------------------------


def test_plan_does_not_modify_anything(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    Rebaser(tmp_path).plan("memory", rewrite_all=True)

    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after


def test_apply_refuses_a_failed_plan(tmp_path):
    make_project(tmp_path, "memory")
    rebaser = Rebaser(tmp_path)
    plan = rebaser.plan("memory")  # same name -> not ok

    with pytest.raises(RebaseError):
        rebaser.apply(plan)


def test_round_trip_rename_preserves_content(tmp_path):
    make_project(tmp_path, ".memory", legacy=True)

    r1 = Rebaser(tmp_path)
    r1.apply(r1.plan("memory"))
    clear_cache()

    r2 = Rebaser(tmp_path)
    r2.apply(r2.plan(ROOT_BASE))
    clear_cache()

    r3 = Rebaser(tmp_path)
    r3.apply(r3.plan("memory"))
    clear_cache()

    assert (tmp_path / "memory" / "timeline" / "entry.md").read_text(
        encoding="utf-8"
    ) == "- 10:00 | hello"
    assert (tmp_path / "src" / "app.py").is_file()
    assert read_pointer(tmp_path) == "memory"


def test_plan_warns_about_entries_left_behind(tmp_path):
    """Unknown files stay put, so the user must be told they are not coming along."""
    base = make_project(tmp_path, "memory")
    (base / "scratch.txt").write_text("stray", encoding="utf-8")
    (base / "my-notes").mkdir()

    plan = Rebaser(tmp_path).plan(ROOT_BASE)

    joined = " ".join(plan.warnings)
    assert "scratch.txt" in joined
    assert "my-notes" in joined


def test_plan_has_no_leftover_warning_when_base_is_clean(tmp_path):
    make_project(tmp_path, "memory")
    plan = Rebaser(tmp_path).plan(ROOT_BASE)

    assert not any("not recognized" in w for w in plan.warnings)
