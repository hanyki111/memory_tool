"""Archiver for module documentation (decisions, current, plans)."""

import re
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime


class ArchiverError(Exception):
    """Base exception for archiver operations."""
    pass


class Archiver:
    """Handle archiving of module documentation."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize archiver.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.module_path = self.memory_path / "modules" / "memory-system"
        self.archive_path = self.module_path / "archive"

    def archive_decisions(
        self,
        phase: int,
        dry_run: bool = False,
    ) -> Tuple[Path, int]:
        """
        Archive decisions up to specified phase.

        Args:
            phase: Phase number to archive up to (inclusive)
            dry_run: If True, show what would be archived without doing it

        Returns:
            (archive_file_path, num_decisions_archived)

        Raises:
            ArchiverError: If archiving fails
        """
        decisions_file = self.module_path / "decisions.md"

        if not decisions_file.exists():
            raise ArchiverError(f"decisions.md not found at {decisions_file}")

        # Read current decisions
        content = decisions_file.read_text(encoding="utf-8")

        # Parse decisions
        decisions = self._parse_decisions(content)

        if not decisions:
            raise ArchiverError("No decisions found in decisions.md")

        # Filter by phase
        to_archive = [d for d in decisions if self._get_decision_phase(d['number']) <= phase]
        to_keep = [d for d in decisions if self._get_decision_phase(d['number']) > phase]

        if not to_archive:
            raise ArchiverError(f"No decisions to archive for phase 1-{phase}")

        # Determine archive file name
        min_num = min(d['number'] for d in to_archive)
        max_num = max(d['number'] for d in to_archive)

        # Find phase range
        min_phase = self._get_decision_phase(min_num)
        max_phase = phase

        if min_phase == max_phase:
            archive_filename = f"decisions-phase{min_phase}.md"
        else:
            archive_filename = f"decisions-phase{min_phase}-{max_phase}.md"

        archive_file = self.archive_path / archive_filename

        if dry_run:
            return (archive_file, len(to_archive))

        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Create backup
        backup_file = decisions_file.with_suffix(".md.bak")
        shutil.copy2(decisions_file, backup_file)

        # Create archive file
        archive_content = self._build_archive_content(to_archive, min_phase, max_phase)
        archive_file.write_text(archive_content, encoding="utf-8")

        # Update decisions.md (keep recent only)
        new_content = self._build_updated_decisions(to_keep, archive_filename, min_num, max_num)
        decisions_file.write_text(new_content, encoding="utf-8")

        # Update decisions-index.md
        self._update_decisions_index(archive_filename, min_num, max_num, min_phase, max_phase)

        return (archive_file, len(to_archive))

    def archive_current(
        self,
        phase: int,
        dry_run: bool = False,
    ) -> Path:
        """
        Archive current.md to archive/current-phaseN.md.

        Args:
            phase: Phase number
            dry_run: If True, show what would be archived without doing it

        Returns:
            Path to archive file

        Raises:
            ArchiverError: If archiving fails
        """
        current_file = self.module_path / "current.md"

        if not current_file.exists():
            raise ArchiverError(f"current.md not found at {current_file}")

        archive_filename = f"current-phase{phase}.md"
        archive_file = self.archive_path / archive_filename

        if dry_run:
            return archive_file

        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Create backup
        backup_file = current_file.with_suffix(".md.bak")
        shutil.copy2(current_file, backup_file)

        # Copy to archive
        shutil.copy2(current_file, archive_file)

        # Reset current.md with template
        template = f"""# Current Status

> **Phase {phase + 1} in progress**

For Phase {phase} status, see [archive/current-phase{phase}.md](./archive/current-phase{phase}.md)

---

## Active Work

### In Progress
-

### Next Steps
-

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
"""
        current_file.write_text(template, encoding="utf-8")

        return archive_file

    def archive_plans(
        self,
        dry_run: bool = False,
    ) -> List[Path]:
        """
        Move PLAN-*.md files to archive/plans/.

        Args:
            dry_run: If True, show what would be archived without doing it

        Returns:
            List of archived file paths

        Raises:
            ArchiverError: If archiving fails
        """
        # Find PLAN-*.md files
        plan_files = list(self.module_path.glob("PLAN-*.md"))

        if not plan_files:
            return []

        if dry_run:
            return [self.archive_path / "plans" / f.name for f in plan_files]

        # Ensure archive/plans directory exists
        plans_archive = self.archive_path / "plans"
        plans_archive.mkdir(parents=True, exist_ok=True)

        archived = []
        for plan_file in plan_files:
            dest = plans_archive / plan_file.name

            # Move file
            shutil.move(str(plan_file), str(dest))
            archived.append(dest)

        return archived

    def _parse_decisions(self, content: str) -> List[Dict]:
        """
        Parse decisions from decisions.md content.

        Args:
            content: Full content of decisions.md

        Returns:
            List of decision dictionaries
        """
        decisions = []

        # Pattern: ### YYYY-MM-DD: Title ... **결정 #N:**
        # Split content by ### headers
        sections = re.split(r'(###\s+\d{4}-\d{2}-\d{2}:.+)', content)

        for i in range(1, len(sections), 2):
            if i + 1 >= len(sections):
                break

            header = sections[i]
            body = sections[i + 1] if i + 1 < len(sections) else ""

            # Extract date and title from header
            header_match = re.match(r'###\s+(\d{4}-\d{2}-\d{2}):\s+(.+)', header)
            if not header_match:
                continue

            date_str, title = header_match.groups()

            # Extract decision number from body
            decision_match = re.search(r'\*\*결정 #(\d+)\*\*', body)
            if not decision_match:
                continue

            decision_num = int(decision_match.group(1))

            # Find end of this decision (next ### or ---)
            end_match = re.search(r'\n---\n', body)
            if end_match:
                body = body[:end_match.start()]

            decisions.append({
                'number': decision_num,
                'date': date_str,
                'title': title.strip(),
                'header': header,
                'content': body.strip(),
            })

        return decisions

    def _get_decision_phase(self, decision_num: int) -> int:
        """
        Get phase number for a decision.

        Uses heuristic based on decision numbers:
        - #1-#23: Phase 1-4
        - #24-#25: Phase 5
        - #26-#28: Phase 5
        - #29+: Phase 6+

        Args:
            decision_num: Decision number

        Returns:
            Phase number
        """
        # Simple heuristic: every ~5-10 decisions = 1 phase
        # For now, use hard-coded mapping based on existing data
        if decision_num <= 23:
            return 4  # Phase 1-4 (archived)
        elif decision_num <= 28:
            return 5  # Phase 5 (current)
        else:
            return 6  # Phase 6+ (future)

    def _build_archive_content(
        self,
        decisions: List[Dict],
        min_phase: int,
        max_phase: int,
    ) -> str:
        """Build content for archive file."""
        lines = []

        # Header
        if min_phase == max_phase:
            lines.append(f"# Key Decisions - Phase {min_phase}")
        else:
            lines.append(f"# Key Decisions - Phase {min_phase}-{max_phase}")

        lines.append("")
        lines.append(f"> **Archived decisions from Phase {min_phase}-{max_phase}**")
        lines.append("")
        lines.append(f"**Archived on:** {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Decisions
        for decision in sorted(decisions, key=lambda d: d['number']):
            lines.append(decision['header'])
            lines.append(decision['content'])
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _build_updated_decisions(
        self,
        remaining_decisions: List[Dict],
        archive_filename: str,
        archived_min: int,
        archived_max: int,
    ) -> str:
        """Build updated decisions.md content with recent decisions only."""
        lines = []

        # Header
        if not remaining_decisions:
            next_phase = self._get_decision_phase(archived_max) + 1
            lines.append("# Key Decisions")
            lines.append("")
            lines.append(f"> **Recent decisions for Phase {next_phase}**")
        else:
            min_remaining = min(d['number'] for d in remaining_decisions)
            phase = self._get_decision_phase(min_remaining)
            lines.append("# Key Decisions")
            lines.append("")
            lines.append(f"> **Recent decisions for Phase {phase}+**")

        lines.append("")
        lines.append(f"For decisions #{archived_min}-#{archived_max}, see [archive/{archive_filename}](./archive/{archive_filename})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Recent decisions
        if remaining_decisions:
            lines.append(f"## Recent Decisions (Phase {phase}+)")
            lines.append("")

            for decision in sorted(remaining_decisions, key=lambda d: d['number'], reverse=True):
                lines.append(decision['header'])
                lines.append(decision['content'])
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def _update_decisions_index(
        self,
        archive_filename: str,
        min_num: int,
        max_num: int,
        min_phase: int,
        max_phase: int,
    ):
        """Update decisions-index.md with archive link."""
        index_file = self.module_path / "decisions-index.md"

        if not index_file.exists():
            return  # Index file doesn't exist, skip

        content = index_file.read_text(encoding="utf-8")

        # Add archive link to index
        archive_line = f"\n- **Decisions #{min_num}-#{max_num}** (Phase {min_phase}-{max_phase}): [archive/{archive_filename}](./archive/{archive_filename})\n"

        # Insert after header
        lines = content.split("\n")
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith("## All Decisions") or line.startswith("---"):
                insert_pos = i + 1
                break

        if insert_pos > 0:
            lines.insert(insert_pos, archive_line)
            index_file.write_text("\n".join(lines), encoding="utf-8")
