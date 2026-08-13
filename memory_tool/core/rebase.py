"""Renaming (re-basing) the knowledge base folder.

Moves the base folder to a new name -- including to and from the project root
itself -- and repairs everything that referenced the old location.

The operation is planned first and applied second, so ``mbase set --dry-run``
can show exactly what will happen before anything is touched. Only known
knowledge-base entries are ever moved: when the base is the project root, the
surrounding project files (``src/``, ``README.md``, ``pyproject.toml`` ...) must
be left strictly alone.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from memory_tool.utils.paths import (
    CONFIG_FILENAME,
    CONTENT_SUBDIRS,
    POINTER_FILENAME,
    ROOT_BASE,
    STATE_ENTRIES,
    InvalidBaseNameError,
    clear_cache,
    resolve_base,
    validate_base_name,
    write_pointer,
)


class RebaseError(Exception):
    """Raised when a base folder rename cannot be performed safely."""


#: Root-level files that commonly document the base folder path. Only rewritten
#: under --rewrite-all, and always listed in the plan first.
ROOT_DOC_FILES = ("CLAUDE.md", "GEMINI.md", "AGENTS.md", "README.md")


@dataclass
class FileRewrite:
    """A single file whose contents reference the old base folder."""

    path: Path
    line_numbers: List[int] = field(default_factory=list)
    scope: str = "related-files"  # or "all"

    @property
    def count(self) -> int:
        return len(self.line_numbers)


@dataclass
class RebasePlan:
    """Everything a rename will do, computed before anything is touched."""

    root: Path
    old_name: str
    new_name: str
    old_base: Path
    new_base: Path
    moves: List[Tuple[Path, Path]] = field(default_factory=list)
    rewrites: List[FileRewrite] = field(default_factory=list)
    gitignore_edit: Optional[Tuple[Path, str, str]] = None  # path, old line, new line
    kb_path_edit: Optional[Tuple[str, str]] = None  # old value, new value
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def rewrite_line_total(self) -> int:
        return sum(r.count for r in self.rewrites)

    @property
    def to_root(self) -> bool:
        return self.new_name == ROOT_BASE

    @property
    def from_root(self) -> bool:
        return self.old_name == ROOT_BASE


class Rebaser:
    """Plans and applies a base folder rename."""

    RELATED_HEADER = re.compile(r"^##\s*(?:\S+\s*)?Related\s+Files", re.IGNORECASE)
    SECTION_BREAK = re.compile(r"^##\s")

    def __init__(self, root: Optional[Path] = None):
        """Initialize the rebaser.

        Args:
            root: Project root. Resolved from the current directory if None.
        """
        paths = resolve_base(root)
        self.paths = paths
        self.root = paths.root
        self.old_name = paths.base_name
        self.old_base = paths.base

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        new_name: str,
        rewrite: bool = True,
        rewrite_all: bool = False,
        update_git: bool = True,
    ) -> RebasePlan:
        """Compute the full rename plan without changing anything.

        Args:
            new_name: Desired base folder name, or "." for the project root
            rewrite: Rewrite markdown references to the old base folder
            rewrite_all: Rewrite all markdown, not just Related Files sections
            update_git: Update a matching .gitignore entry

        Returns:
            A RebasePlan. Check ``plan.ok`` before applying.

        Raises:
            RebaseError: If the requested name is unusable.
        """
        try:
            normalized = validate_base_name(new_name)
        except InvalidBaseNameError as e:
            raise RebaseError(str(e)) from e

        new_base = self.root if normalized == ROOT_BASE else self.root / normalized

        plan = RebasePlan(
            root=self.root,
            old_name=self.old_name,
            new_name=normalized,
            old_base=self.old_base,
            new_base=new_base,
        )

        if not self.paths.found or not self.old_base.is_dir():
            plan.errors.append(
                f"No initialized knowledge base found at {self.old_base}. "
                f"Run 'minit' first."
            )
            return plan

        if normalized == self.old_name:
            plan.errors.append(
                f"The base folder is already '{self.old_name}' -- nothing to do."
            )
            return plan

        self._plan_moves(plan)
        if plan.errors:
            return plan

        if rewrite:
            self._plan_rewrites(plan, rewrite_all=rewrite_all)
        if update_git:
            self._plan_gitignore(plan)

        self._plan_kb_path(plan)
        self._add_advisories(plan)

        return plan

    def _plan_moves(self, plan: RebasePlan) -> None:
        """Decide which entries move where, and detect collisions."""
        # Case 1: subfolder -> subfolder. Move the directory as a whole.
        if not plan.from_root and not plan.to_root:
            if plan.new_base.exists():
                if plan.new_base.is_dir() and not any(plan.new_base.iterdir()):
                    pass  # empty target directory is fine
                else:
                    plan.errors.append(
                        f"Target '{plan.new_name}' already exists and is not empty: "
                        f"{plan.new_base}"
                    )
                    return
            plan.moves.append((plan.old_base, plan.new_base))
            return

        # Case 2 & 3: one side is the project root, so move entry by entry.
        # Only known knowledge-base entries move -- never unrelated project files.
        known = list(CONTENT_SUBDIRS) + list(STATE_ENTRIES) + [CONFIG_FILENAME]
        found_any = False

        for name in known:
            source = plan.old_base / name
            if not source.exists():
                continue
            found_any = True
            target = plan.new_base / name
            if target.exists():
                plan.errors.append(
                    f"Cannot move '{name}': target already exists at {target}"
                )
                continue
            plan.moves.append((source, target))

        if not found_any:
            plan.errors.append(
                f"No knowledge base content found in {plan.old_base} "
                f"(looked for {', '.join(CONTENT_SUBDIRS)}, {CONFIG_FILENAME})."
            )
            return

        # Anything unrecognized is deliberately left where it is -- but say so,
        # otherwise files appear to vanish from the knowledge base.
        if not plan.from_root:
            known_set = set(known) | {POINTER_FILENAME}
            leftovers = sorted(
                p.name for p in plan.old_base.iterdir() if p.name not in known_set
            )
            if leftovers:
                plan.warnings.append(
                    f"These entries are not recognized as knowledge base content and "
                    f"will stay in '{plan.old_name}/': {', '.join(leftovers[:10])}"
                    f"{' ...' if len(leftovers) > 10 else ''}. Move them by hand if "
                    f"you want them in the new location."
                )

    def _iter_markdown(self, rewrite_all: bool):
        """Yield markdown files in scope for reference rewriting."""
        modules_dir = self.old_base / "modules"

        if not rewrite_all:
            if modules_dir.is_dir():
                yield from sorted(modules_dir.rglob("*.md"))
            return

        # --rewrite-all: every markdown file in the knowledge base, plus the
        # root-level documents that describe where the base folder lives.
        for sub in CONTENT_SUBDIRS:
            d = self.old_base / sub
            if d.is_dir():
                yield from sorted(d.rglob("*.md"))

        for name in ROOT_DOC_FILES:
            f = self.root / name
            if f.is_file():
                yield f

        claude_dir = self.root / ".claude"
        if claude_dir.is_dir():
            yield from sorted(claude_dir.glob("*.md"))

    def _matching_lines(self, path: Path, rewrite_all: bool) -> List[int]:
        """Line numbers in `path` that reference the old base folder."""
        try:
            lines = path.read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            return []

        needle = f"{self.old_name}/"
        hits: List[int] = []
        inside_related = False

        for i, line in enumerate(lines, 1):
            if not rewrite_all:
                # Track whether we are inside a Related Files section.
                if self.RELATED_HEADER.match(line):
                    inside_related = True
                    continue
                if inside_related and self.SECTION_BREAK.match(line):
                    inside_related = False
                    continue
                if not inside_related:
                    continue

            if needle in line:
                hits.append(i)

        return hits

    def _plan_rewrites(self, plan: RebasePlan, rewrite_all: bool) -> None:
        """Find markdown references to the old base folder."""
        if plan.from_root:
            # Paths under a root base have no distinguishing prefix, so there is
            # nothing safe to search for -- rewriting bare paths would corrupt
            # unrelated text.
            plan.warnings.append(
                "Old base is the project root, so markdown references have no "
                "folder prefix to rewrite. Reference rewriting skipped."
            )
            return

        scope = "all" if rewrite_all else "related-files"
        for path in self._iter_markdown(rewrite_all):
            hits = self._matching_lines(path, rewrite_all)
            if hits:
                plan.rewrites.append(FileRewrite(path=path, line_numbers=hits, scope=scope))

    def _plan_gitignore(self, plan: RebasePlan) -> None:
        """Find a .gitignore entry matching the old base folder."""
        gitignore = self.root / ".gitignore"
        if not gitignore.is_file() or plan.from_root:
            return

        candidates = {
            self.old_name,
            f"{self.old_name}/",
            f"/{self.old_name}",
            f"/{self.old_name}/",
        }

        try:
            lines = gitignore.read_text(encoding="utf-8").split("\n")
        except OSError:
            return

        for line in lines:
            if line.strip() in candidates:
                if plan.to_root:
                    # The project root cannot ignore itself; comment it out and
                    # make the consequence explicit.
                    new_line = (
                        f"# {line.strip()}  # base folder moved to the project root by mbase"
                    )
                    plan.warnings.append(
                        "The knowledge base is moving to the project root, so the "
                        f"'{line.strip()}' ignore rule no longer applies. It will be "
                        "commented out and your knowledge base will become visible "
                        "to git. Review 'git status' before committing."
                    )
                else:
                    new_line = line.replace(self.old_name, plan.new_name)
                    plan.warnings.append(
                        f".gitignore rule '{line.strip()}' will become "
                        f"'{new_line.strip()}', so the knowledge base stays ignored. "
                        f"Remove it if you now want the folder tracked (for example "
                        f"to sync an Obsidian vault)."
                    )
                plan.gitignore_edit = (gitignore, line, new_line)
                return

    def _plan_kb_path(self, plan: RebasePlan) -> None:
        """Check whether config's kb.path points into the folder being moved."""
        from memory_tool.utils.config import Config

        try:
            config = Config(self.old_base)
            kb_path = config.get_kb_path()
        except Exception:
            return

        if not kb_path:
            return

        try:
            inside = kb_path.resolve().is_relative_to(self.old_base.resolve())
        except (OSError, ValueError):
            inside = False

        if inside:
            rel = kb_path.resolve().relative_to(self.old_base.resolve())
            new_value = str(plan.new_base / rel)
            plan.kb_path_edit = (str(kb_path), new_value)
        else:
            plan.warnings.append(
                f"config kb.path points outside this project ({kb_path}) and will "
                f"not be changed. If that knowledge base is renamed too, update "
                f"this project's kb.path by hand."
            )

    def _add_advisories(self, plan: RebasePlan) -> None:
        """Add warnings that are not tied to a specific edit."""
        moved_state = [
            src.name for src, _ in plan.moves if src.name in set(STATE_ENTRIES)
        ]
        if moved_state or not plan.from_root:
            plan.warnings.append(
                "Generated caches and indexes are keyed by absolute path, so they "
                "will be stale after the move. Rebuild them when convenient "
                "(searching re-indexes as needed)."
            )

        plan.warnings.append(
            "Other projects that reference this one (their config kb.path) will "
            "still point at the old location. Update them by hand."
        )

        if plan.to_root:
            plan.warnings.append(
                "With the base at the project root, only the known content folders "
                f"({', '.join(CONTENT_SUBDIRS)}) are searched and indexed. Notes "
                "kept anywhere else in the project will not be found."
            )

    # ------------------------------------------------------------------
    # Applying
    # ------------------------------------------------------------------

    def apply(self, plan: RebasePlan) -> dict:
        """Execute a plan.

        Moves happen first and are rolled back on failure, so a partial move
        never leaves the knowledge base split across two locations.

        Args:
            plan: A plan from `plan()` with ``ok`` True

        Returns:
            Summary dict of what was changed.

        Raises:
            RebaseError: If the plan is not applicable, or a move fails.
        """
        if not plan.ok:
            raise RebaseError("; ".join(plan.errors))

        result = {
            "moved": [],
            "rewritten": [],
            "pointer": None,
            "gitignore": None,
            "kb_path": None,
        }

        if plan.to_root:
            plan.new_base.mkdir(parents=True, exist_ok=True)
        elif not plan.from_root:
            plan.new_base.parent.mkdir(parents=True, exist_ok=True)
        else:
            plan.new_base.mkdir(parents=True, exist_ok=True)

        done: List[Tuple[Path, Path]] = []
        try:
            for source, target in plan.moves:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
                done.append((source, target))
                result["moved"].append((source, target))
        except Exception as e:
            for source, target in reversed(done):
                try:
                    shutil.move(str(target), str(source))
                except Exception:
                    raise RebaseError(
                        f"Move failed ({e}) and rollback also failed. The knowledge "
                        f"base is split between {plan.old_base} and {plan.new_base} "
                        f"-- move the remaining entries back by hand."
                    ) from e
            raise RebaseError(f"Move failed, rolled back cleanly: {e}") from e

        # Remove the now-empty old base folder (never when it was the root).
        if not plan.from_root and plan.old_base.is_dir():
            try:
                if not any(plan.old_base.iterdir()):
                    plan.old_base.rmdir()
            except OSError:
                pass

        result["pointer"] = write_pointer(self.root, plan.new_name)

        for rw in plan.rewrites:
            if self._apply_rewrite(rw, plan):
                result["rewritten"].append(rw.path)

        if plan.gitignore_edit:
            path, old_line, new_line = plan.gitignore_edit
            try:
                content = path.read_text(encoding="utf-8")
                path.write_text(content.replace(old_line, new_line, 1), encoding="utf-8")
                result["gitignore"] = path
            except OSError:
                plan.warnings.append(f"Could not update {path}; edit it by hand.")

        if plan.kb_path_edit:
            _, new_value = plan.kb_path_edit
            try:
                from memory_tool.utils.config import Config

                Config(plan.new_base).set_kb_path(new_value)
                result["kb_path"] = new_value
            except Exception:
                plan.warnings.append(
                    f"Could not update config kb.path to {new_value}; set it by hand."
                )

        clear_cache()
        return result

    def _apply_rewrite(self, rw: FileRewrite, plan: RebasePlan) -> bool:
        """Rewrite old-base references in one file, after the move."""
        # The file has moved with the base folder, so resolve its new location.
        path = rw.path
        if not path.exists():
            try:
                rel = rw.path.relative_to(plan.old_base)
                path = plan.new_base / rel
            except ValueError:
                return False
        if not path.exists():
            return False

        old_prefix = f"{plan.old_name}/"
        new_prefix = "" if plan.to_root else f"{plan.new_name}/"

        try:
            lines = path.read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            return False

        changed = False
        inside_related = False
        out = []
        for line in lines:
            if rw.scope != "all":
                if self.RELATED_HEADER.match(line):
                    inside_related = True
                    out.append(line)
                    continue
                if inside_related and self.SECTION_BREAK.match(line):
                    inside_related = False
                    out.append(line)
                    continue
                if not inside_related:
                    out.append(line)
                    continue

            if old_prefix in line:
                out.append(line.replace(old_prefix, new_prefix))
                changed = True
            else:
                out.append(line)

        if changed:
            try:
                path.write_text("\n".join(out), encoding="utf-8")
            except OSError:
                return False
        return changed
