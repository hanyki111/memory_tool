"""Repair wiki links after modules are moved by hand.

Modules are plain files in a folder, so the natural way to reorganize them is to
drag them in Obsidian or a file manager rather than to run a command. Discovery
copes with that already -- it scans the filesystem, so a moved module is simply
found at its new location.

What does not cope is everything pointing *at* the module. ``[[old/path]]`` links
in other modules keep naming a location that no longer exists, and because a
broken link renders as ordinary text rather than an error, the breakage is
silent. This module finds those links and repoints them.

Detection is deliberately stateless: rather than tracking moves as they happen,
it reads the current state and asks "which links name a module that is not
there, and is there exactly one module it could now be?". A move that leaves no
broken link needs no repair, and a move that is ambiguous is reported instead of
guessed at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from memory_tool.core.connections import ConnectionParser
from memory_tool.core.module import ModuleManager


@dataclass(frozen=True)
class LinkRef:
    """One ``[[target]]`` occurrence in a module file."""

    module: str
    file: Path
    line_no: int
    target: str


@dataclass
class Proposal:
    """A broken target that resolves to exactly one existing module."""

    old: str
    new: str
    refs: List[LinkRef] = field(default_factory=list)

    @property
    def reason(self) -> str:
        old_base = _basename(self.old)
        new_base = _basename(self.new)
        if old_base == new_base:
            return f"moved to {self.new}"
        return f"renamed to {self.new}"


@dataclass
class Unresolved:
    """A broken target that cannot be repaired automatically."""

    target: str
    refs: List[LinkRef] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        if not self.candidates:
            return "no module with that name exists"
        return "ambiguous: " + ", ".join(self.candidates)


@dataclass
class RelinkPlan:
    """Everything found in one scan."""

    proposals: List[Proposal] = field(default_factory=list)
    unresolved: List[Unresolved] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.proposals and not self.unresolved

    @property
    def link_count(self) -> int:
        return sum(len(p.refs) for p in self.proposals)

    @property
    def file_count(self) -> int:
        return len({ref.file for p in self.proposals for ref in p.refs})


def _normalize(target: str) -> str:
    """Normalize a link target for comparison (separators, stray slashes)."""
    return target.replace("\\", "/").strip("/").strip()


def _basename(target: str) -> str:
    return _normalize(target).split("/")[-1]


def link_pattern_for(target: str) -> re.Pattern:
    """Build a pattern matching ``[[target]]`` and its alias/section variants.

    The target is matched with optional surrounding whitespace and either
    separator, so a link written ``[[a\\b]]`` or ``[[ a/b ]]`` is repaired too.
    Alias, section and block suffixes are captured so they survive the rewrite --
    losing an alias would silently change what the document reads like.
    """
    normalized = _normalize(target)
    # Match either separator between segments.
    escaped = r"[\\/]".join(re.escape(part) for part in normalized.split("/"))

    return re.compile(
        r"\[\[\s*" + escaped + r"\s*"
        r"((?:[#^][^\[\]|]*)?(?:\|[^\[\]]*)?)"  # suffixes to preserve
        r"\]\]"
    )


def module_files(manager: ModuleManager) -> Dict[str, Path]:
    """Map every discovered module to the markdown file holding it.

    Legacy multi-file modules are represented by their directory, so the mapping
    falls back to the directory itself; callers scan whatever markdown is inside.
    """
    mapping: Dict[str, Path] = {}

    for rel in manager.discover_all_modules():
        name = str(rel).replace("\\", "/")
        try:
            path = manager.get_module_file_path(name)
        except Exception:
            path = manager.modules_path / rel

        mapping[name] = path

    return mapping


def _files_to_scan(manager: ModuleManager, module: str, primary: Path) -> List[Path]:
    """Markdown files belonging to one module."""
    if primary.is_file():
        return [primary]

    directory = manager.modules_path / module
    if directory.is_dir():
        return sorted(p for p in directory.glob("*.md") if p.is_file())

    return []


def scan_links(manager: Optional[ModuleManager] = None) -> List[LinkRef]:
    """Collect every wiki link in every module.

    Reads the files rather than the connection database: the database is a cache
    that may predate the move being repaired, and repairing links from a stale
    cache would rewrite the wrong things.
    """
    manager = manager or ModuleManager()
    refs: List[LinkRef] = []

    for module, path in module_files(manager).items():
        for file_path in _files_to_scan(manager, module, path):
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            for line_no, line in enumerate(content.split("\n"), 1):
                for match in ConnectionParser.LINK_PATTERN.finditer(line):
                    target = match.group(1).strip()
                    if target:
                        refs.append(LinkRef(module, file_path, line_no, target))

    return refs


def _candidates(target: str, existing: Dict[str, Path]) -> List[str]:
    """Modules a broken target could plausibly refer to.

    Two rules, most specific first:
      1. the target is a suffix of the module path -- "b" matching "a/b"
      2. the final segment matches -- "x/b" matching "a/b" after a move

    A suffix match is preferred because it is strictly more evidence; falling
    straight to basename matching would call ``a/b`` and ``c/b`` equally likely
    even when the link already said ``b``.
    """
    normalized = _normalize(target)
    base = _basename(target)

    suffix = [
        name
        for name in existing
        if name == normalized or name.endswith("/" + normalized)
    ]
    if suffix:
        return sorted(suffix)

    return sorted(name for name in existing if _basename(name) == base)


def build_plan(manager: Optional[ModuleManager] = None) -> RelinkPlan:
    """Work out which links are broken and what they should point at."""
    manager = manager or ModuleManager()
    existing = module_files(manager)
    known = {_normalize(name) for name in existing}

    broken: Dict[str, List[LinkRef]] = {}
    for ref in scan_links(manager):
        if _normalize(ref.target) not in known:
            broken.setdefault(_normalize(ref.target), []).append(ref)

    plan = RelinkPlan()

    for target in sorted(broken):
        refs = broken[target]
        options = _candidates(target, existing)

        if len(options) == 1:
            plan.proposals.append(Proposal(old=target, new=options[0], refs=refs))
        else:
            plan.unresolved.append(
                Unresolved(target=target, refs=refs, candidates=options)
            )

    return plan


def apply_plan(plan: RelinkPlan, dry_run: bool = False) -> int:
    """Rewrite the proposed links.

    Args:
        plan: Plan from :func:`build_plan`
        dry_run: Report what would change without writing

    Returns:
        Number of files modified (or that would be).
    """
    if not plan.proposals:
        return 0

    # Group by file so each file is read and written once even when several
    # different targets inside it moved.
    by_file: Dict[Path, List[Proposal]] = {}
    for proposal in plan.proposals:
        for ref in proposal.refs:
            bucket = by_file.setdefault(ref.file, [])
            if proposal not in bucket:
                bucket.append(proposal)

    changed = 0

    for file_path, proposals in by_file.items():
        try:
            original = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        updated = original
        for proposal in proposals:
            pattern = link_pattern_for(proposal.old)
            # "\g<1>" keeps any alias/section suffix that followed the target.
            updated = pattern.sub(f"[[{proposal.new}\\g<1>]]", updated)

        if updated != original:
            changed += 1
            if not dry_run:
                file_path.write_text(updated, encoding="utf-8")

    return changed


def format_plan(plan: RelinkPlan, dry_run: bool = False) -> str:
    """Render a plan for the terminal."""
    if plan.is_empty:
        return "No broken module links found."

    lines: List[str] = []

    if plan.proposals:
        header = "Would repair" if dry_run else "Repaired"
        lines.append(
            f"{header} {plan.link_count} link(s) across {plan.file_count} file(s):"
        )
        for proposal in plan.proposals:
            lines.append(f"  [[{proposal.old}]] -> [[{proposal.new}]]  ({proposal.reason})")
            for ref in proposal.refs:
                lines.append(f"      {ref.module}:{ref.line_no}")

    if plan.unresolved:
        if lines:
            lines.append("")
        lines.append(f"Needs a decision ({len(plan.unresolved)}):")
        for item in plan.unresolved:
            lines.append(f"  [[{item.target}]] -- {item.reason}")
            for ref in item.refs:
                lines.append(f"      {ref.module}:{ref.line_no}")

    return "\n".join(lines)
