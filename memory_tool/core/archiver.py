"""Archiver for module documentation (decisions, current, plans)."""

import re
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser


class ArchiverError(Exception):
    """Base exception for archiver operations."""
    pass


class Archiver:
    """Handle archiving of module documentation."""

    def __init__(self, base_path: Optional[Path] = None, module_name: Optional[str] = None):
        """
        Initialize archiver.

        Args:
            base_path: Base path for project. Defaults to current directory.
            module_name: Module name or path (e.g., 'memory-system' or 'projects/website').
                        Defaults to 'memory-system' for backwards compatibility.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"

        # Default to memory-system for backwards compatibility
        if module_name is None:
            module_name = "memory-system"

        self.module_name = module_name
        self.module_path = self.memory_path / "modules" / module_name
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

    def archive_decisions_by_number(
        self,
        up_to: int,
        dry_run: bool = False,
    ) -> Tuple[Path, int]:
        """
        Archive decisions up to specified decision number.

        Args:
            up_to: Decision number to archive up to (inclusive, e.g., 25 = archive #1-#25)
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

        # Filter by decision number
        to_archive = [d for d in decisions if d['number'] <= up_to]
        to_keep = [d for d in decisions if d['number'] > up_to]

        if not to_archive:
            raise ArchiverError(f"No decisions to archive up to #{up_to}")

        # Determine archive file name (use decision number range)
        min_num = min(d['number'] for d in to_archive)
        max_num = max(d['number'] for d in to_archive)
        archive_filename = f"decisions-{min_num}-{max_num}.md"

        archive_file = self.archive_path / archive_filename

        if dry_run:
            return (archive_file, len(to_archive))

        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Create backup
        backup_file = decisions_file.with_suffix(".md.bak")
        shutil.copy2(decisions_file, backup_file)

        # Create archive file (without phase info)
        archive_content = self._build_archive_content_by_number(to_archive, min_num, max_num)
        archive_file.write_text(archive_content, encoding="utf-8")

        # Update decisions.md (keep recent only)
        new_content = self._build_updated_decisions_by_number(to_keep, archive_filename, min_num, max_num)
        decisions_file.write_text(new_content, encoding="utf-8")

        # Update decisions-index.md (without phase)
        self._update_decisions_index_by_number(archive_filename, min_num, max_num)

        return (archive_file, len(to_archive))

    def archive_decisions_by_count(
        self,
        keep_recent: int,
        dry_run: bool = False,
    ) -> Tuple[Path, int]:
        """
        Archive decisions, keeping only the N most recent ones.

        Args:
            keep_recent: Number of recent decisions to keep (e.g., 10 = keep most recent 10)
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

        total_count = len(decisions)

        if total_count <= keep_recent:
            raise ArchiverError(f"Only {total_count} decisions exist, cannot archive (keeping {keep_recent})")

        # Sort by decision number (ascending)
        sorted_decisions = sorted(decisions, key=lambda d: d['number'])

        # Archive oldest, keep most recent
        num_to_archive = total_count - keep_recent
        to_archive = sorted_decisions[:num_to_archive]
        to_keep = sorted_decisions[num_to_archive:]

        # Determine archive file name
        min_num = min(d['number'] for d in to_archive)
        max_num = max(d['number'] for d in to_archive)
        archive_filename = f"decisions-{min_num}-{max_num}.md"

        archive_file = self.archive_path / archive_filename

        if dry_run:
            return (archive_file, len(to_archive))

        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Create backup
        backup_file = decisions_file.with_suffix(".md.bak")
        shutil.copy2(decisions_file, backup_file)

        # Create archive file
        archive_content = self._build_archive_content_by_number(to_archive, min_num, max_num)
        archive_file.write_text(archive_content, encoding="utf-8")

        # Update decisions.md (keep recent only)
        new_content = self._build_updated_decisions_by_number(to_keep, archive_filename, min_num, max_num)
        decisions_file.write_text(new_content, encoding="utf-8")

        # Update decisions-index.md
        self._update_decisions_index_by_number(archive_filename, min_num, max_num)

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
            decision_match = re.search(r'\*\*결정 #(\d+):', body)
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

    def _build_archive_content_by_number(
        self,
        decisions: List[Dict],
        min_num: int,
        max_num: int,
    ) -> str:
        """Build content for archive file (by decision number)."""
        lines = []

        # Header
        lines.append(f"# Key Decisions #{min_num}-#{max_num}")
        lines.append("")
        lines.append(f"> **Archived decisions #{min_num}-#{max_num}**")
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

    def _build_updated_decisions_by_number(
        self,
        remaining_decisions: List[Dict],
        archive_filename: str,
        archived_min: int,
        archived_max: int,
    ) -> str:
        """Build updated decisions.md content with recent decisions only (by number)."""
        lines = []

        # Header
        lines.append("# Key Decisions")
        lines.append("")
        if remaining_decisions:
            min_remaining = min(d['number'] for d in remaining_decisions)
            lines.append(f"> **Recent decisions (from #{min_remaining})**")
        else:
            lines.append("> **No recent decisions**")

        lines.append("")
        lines.append(f"For decisions #{archived_min}-#{archived_max}, see [archive/{archive_filename}](./archive/{archive_filename})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Recent decisions
        if remaining_decisions:
            lines.append("## Recent Decisions")
            lines.append("")

            for decision in sorted(remaining_decisions, key=lambda d: d['number'], reverse=True):
                lines.append(decision['header'])
                lines.append(decision['content'])
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def _update_decisions_index_by_number(
        self,
        archive_filename: str,
        min_num: int,
        max_num: int,
    ):
        """Update decisions-index.md with archive link (by decision number)."""
        index_file = self.module_path / "decisions-index.md"

        if not index_file.exists():
            return  # Index file doesn't exist, skip

        content = index_file.read_text(encoding="utf-8")

        # Add archive link to index
        archive_line = f"\n- **Decisions #{min_num}-#{max_num}**: [archive/{archive_filename}](./archive/{archive_filename})\n"

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

    # ============================================================================
    # Phase 5a: New features - Date-based archiving, Auto-suggestion
    # ============================================================================

    def _parse_duration(self, duration_str: str) -> timedelta:
        """
        Parse duration string to timedelta.

        Supported formats:
        - "6m" or "6M" = 6 months
        - "1y" or "1Y" = 1 year
        - "180d" or "180D" = 180 days
        - "4w" or "4W" = 4 weeks

        Args:
            duration_str: Duration string

        Returns:
            timedelta object

        Raises:
            ArchiverError: If format is invalid
        """
        match = re.match(r'^(\d+)([mMdDwWyY])$', duration_str.strip())
        if not match:
            raise ArchiverError(
                f"Invalid duration format: '{duration_str}'. "
                f"Use: 6m (months), 1y (year), 180d (days), 4w (weeks)"
            )

        value = int(match.group(1))
        unit = match.group(2).lower()

        if unit == 'd':
            return timedelta(days=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        elif unit == 'm':
            # Approximate: 1 month = 30 days
            return timedelta(days=value * 30)
        elif unit == 'y':
            # Approximate: 1 year = 365 days
            return timedelta(days=value * 365)
        else:
            raise ArchiverError(f"Unknown duration unit: {unit}")

    def _parse_decision_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse decision date string.

        Args:
            date_str: Date string (YYYY-MM-DD format)

        Returns:
            datetime object or None if parsing fails
        """
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            # Try flexible parsing
            try:
                return date_parser.parse(date_str)
            except:
                return None

    def archive_decisions_by_date(
        self,
        older_than: str,
        dry_run: bool = False,
    ) -> Tuple[Path, int]:
        """
        Archive decisions older than specified duration.

        Args:
            older_than: Duration string (e.g., "6m", "1y", "180d")
            dry_run: If True, show what would be archived without doing it

        Returns:
            (archive_file_path, num_decisions_archived)

        Raises:
            ArchiverError: If archiving fails
        """
        decisions_file = self.module_path / "decisions.md"

        if not decisions_file.exists():
            raise ArchiverError(f"decisions.md not found at {decisions_file}")

        # Parse duration
        duration = self._parse_duration(older_than)
        cutoff_date = datetime.now() - duration

        # Read current decisions
        content = decisions_file.read_text(encoding="utf-8")

        # Parse decisions
        decisions = self._parse_decisions(content)

        if not decisions:
            raise ArchiverError("No decisions found in decisions.md")

        # Filter by date
        to_archive = []
        to_keep = []

        for decision in decisions:
            decision_date = self._parse_decision_date(decision['date'])
            if decision_date and decision_date < cutoff_date:
                to_archive.append(decision)
            else:
                to_keep.append(decision)

        if not to_archive:
            raise ArchiverError(
                f"No decisions older than {older_than} "
                f"(cutoff: {cutoff_date.strftime('%Y-%m-%d')})"
            )

        # Determine archive file name (by date range)
        dates = [self._parse_decision_date(d['date']) for d in to_archive]
        dates = [d for d in dates if d]  # Filter None

        if dates:
            min_date = min(dates)
            max_date = max(dates)
            archive_filename = f"decisions-{min_date.strftime('%Y%m')}-{max_date.strftime('%Y%m')}.md"
        else:
            # Fallback to decision number range
            min_num = min(d['number'] for d in to_archive)
            max_num = max(d['number'] for d in to_archive)
            archive_filename = f"decisions-{min_num}-{max_num}.md"

        archive_file = self.archive_path / archive_filename

        if dry_run:
            return (archive_file, len(to_archive))

        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Create backup
        backup_file = decisions_file.with_suffix(".md.bak")
        shutil.copy2(decisions_file, backup_file)

        # Create archive file
        min_num = min(d['number'] for d in to_archive)
        max_num = max(d['number'] for d in to_archive)
        archive_content = self._build_archive_content_by_number(to_archive, min_num, max_num)
        archive_file.write_text(archive_content, encoding="utf-8")

        # Update decisions.md (keep recent only)
        new_content = self._build_updated_decisions_by_number(to_keep, archive_filename, min_num, max_num)
        decisions_file.write_text(new_content, encoding="utf-8")

        # Update decisions-index.md
        self._update_decisions_index_by_number(archive_filename, min_num, max_num)

        return (archive_file, len(to_archive))

    def suggest_archive(
        self,
        age_threshold_months: int = 6,
    ) -> Dict[str, any]:
        """
        Analyze decisions.md and suggest what to archive.

        Args:
            age_threshold_months: Age threshold in months (default: 6)

        Returns:
            Dictionary with suggestion details

        Raises:
            ArchiverError: If analysis fails
        """
        decisions_file = self.module_path / "decisions.md"

        if not decisions_file.exists():
            raise ArchiverError(f"decisions.md not found at {decisions_file}")

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=age_threshold_months * 30)

        # Read current decisions
        content = decisions_file.read_text(encoding="utf-8")

        # Parse decisions
        decisions = self._parse_decisions(content)

        if not decisions:
            raise ArchiverError("No decisions found in decisions.md")

        # Analyze decisions
        to_archive = []
        to_keep = []
        total_lines = len(content.split("\n"))

        for decision in decisions:
            decision_date = self._parse_decision_date(decision["date"])
            if decision_date and decision_date < cutoff_date:
                to_archive.append(decision)
            else:
                to_keep.append(decision)

        # Calculate estimated sizes
        if to_archive:
            archive_lines = sum(len(d["content"].split("\n")) for d in to_archive)
            remaining_lines = total_lines - archive_lines
        else:
            archive_lines = 0
            remaining_lines = total_lines

        # Build summary
        summary_lines = []
        summary_lines.append(f"Archive Suggestion for {self.module_name}/decisions.md")
        summary_lines.append("=" * 60)
        summary_lines.append(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')} ({age_threshold_months} months ago)")
        summary_lines.append("")

        if to_archive:
            min_num = min(d["number"] for d in to_archive)
            max_num = max(d["number"] for d in to_archive)
            dates = [self._parse_decision_date(d["date"]) for d in to_archive if self._parse_decision_date(d["date"])]
            min_date = min(dates).strftime("%Y-%m-%d") if dates else "Unknown"
            max_date = max(dates).strftime("%Y-%m-%d") if dates else "Unknown"

            summary_lines.append("Suggestions:")
            summary_lines.append(f"  - Archive {len(to_archive)} decisions (#{min_num}-#{max_num})")
            summary_lines.append(f"  - Date range: {min_date} to {max_date}")
            summary_lines.append(f"  - Keep {len(to_keep)} recent decisions")
            summary_lines.append("")
            summary_lines.append("Estimated sizes:")
            summary_lines.append(f"  - Current file: ~{total_lines} lines")
            summary_lines.append(f"  - After archive: ~{remaining_lines} lines ({int(remaining_lines/total_lines*100)}%)")
            summary_lines.append(f"  - Archive file: ~{archive_lines} lines")
        else:
            summary_lines.append(f"No decisions older than {age_threshold_months} months.")
            summary_lines.append(f"All {len(to_keep)} decisions are recent.")

        return {
            "to_archive": to_archive,
            "to_keep": to_keep,
            "cutoff_date": cutoff_date,
            "summary": "\n".join(summary_lines),
            "archive_count": len(to_archive),
            "keep_count": len(to_keep),
        }

    def archive_decisions_interactive(
        self,
        age_threshold_months: int = 6,
        dry_run: bool = False,
    ) -> Tuple[Path, int]:
        """
        Interactively select and archive decisions.

        Args:
            age_threshold_months: Age threshold for initial suggestions (default: 6)
            dry_run: If True, only show what would be archived

        Returns:
            Tuple of (archive file path, number of decisions archived)

        Raises:
            ArchiverError: If archiving fails
        """
        from rich.console import Console
        from rich.prompt import Prompt, Confirm
        from rich.table import Table

        console = Console()

        # Get suggestions
        suggestions = self.suggest_archive(age_threshold_months)

        if suggestions["archive_count"] == 0:
            console.print(f"[yellow]No decisions older than {age_threshold_months} months found.[/yellow]")
            console.print("Nothing to archive.")
            raise ArchiverError("No decisions to archive")

        # Show suggestions
        console.print("\n[bold cyan]Archive Candidates:[/bold cyan]")
        console.print(f"Found {suggestions['archive_count']} decisions older than {age_threshold_months} months\n")

        # Build decision table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Select", justify="center", width=8)
        table.add_column("#", justify="right", width=5)
        table.add_column("Date", width=12)
        table.add_column("Title", no_wrap=False)

        # Display decisions with selection indices
        for idx, decision in enumerate(suggestions["to_archive"], 1):
            # Extract title from content (first line after "## Decision #X:")
            lines = decision["content"].strip().split("\n")
            title = lines[0] if lines else "No title"
            if title.startswith("## Decision"):
                title = lines[1] if len(lines) > 1 else "No title"
            title = title.strip("- ").strip()

            table.add_row(
                f"[{idx}]",
                str(decision["number"]),
                decision["date"],
                title[:60] + "..." if len(title) > 60 else title
            )

        console.print(table)
        console.print()

        # Ask user to select decisions
        console.print("[dim]Enter decision numbers to archive (comma-separated), or 'all' for all:[/dim]")
        console.print("[dim]Example: 1,3,5  or  1-5  or  all[/dim]")

        selection = Prompt.ask("Select", default="all")

        # Parse selection
        selected_indices = set()
        if selection.strip().lower() == "all":
            selected_indices = set(range(1, len(suggestions["to_archive"]) + 1))
        else:
            # Parse comma-separated numbers and ranges
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    # Range like "1-5"
                    try:
                        start, end = part.split("-")
                        start_idx = int(start.strip())
                        end_idx = int(end.strip())
                        selected_indices.update(range(start_idx, end_idx + 1))
                    except ValueError:
                        console.print(f"[yellow]Invalid range: {part}[/yellow]")
                else:
                    # Single number
                    try:
                        selected_indices.add(int(part))
                    except ValueError:
                        console.print(f"[yellow]Invalid number: {part}[/yellow]")

        # Filter selected decisions
        selected_decisions = [
            suggestions["to_archive"][idx - 1]
            for idx in sorted(selected_indices)
            if 1 <= idx <= len(suggestions["to_archive"])
        ]

        if not selected_decisions:
            console.print("[yellow]No valid decisions selected.[/yellow]")
            raise ArchiverError("No decisions selected")

        # Show selection summary
        console.print(f"\n[green]Selected {len(selected_decisions)} decision(s) for archiving:[/green]")
        for decision in selected_decisions:
            console.print(f"  - Decision #{decision['number']} ({decision['date']})")

        # Confirm
        if not dry_run:
            if not Confirm.ask("\nProceed with archiving?", default=True):
                console.print("[yellow]Archiving cancelled.[/yellow]")
                raise ArchiverError("User cancelled archiving")

        # Archive selected decisions
        decisions_file = self.module_path / "decisions.md"
        content = decisions_file.read_text(encoding="utf-8")

        # Get decision numbers to archive
        numbers_to_archive = [d["number"] for d in selected_decisions]

        # Create archive file name
        dates = [self._parse_decision_date(d["date"]) for d in selected_decisions if self._parse_decision_date(d["date"])]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            archive_file_name = f"decisions-{min_date.strftime('%Y%m')}-{max_date.strftime('%Y%m')}.md"
        else:
            archive_file_name = f"decisions-interactive-{datetime.now().strftime('%Y%m%d')}.md"

        archive_file = self.archive_path / archive_file_name

        if dry_run:
            console.print(f"\n[bold]Dry run - would archive to:[/bold]")
            console.print(f"  {archive_file}")
            console.print(f"\n[bold]Mode:[/bold] interactive")
            return archive_file, len(selected_decisions)

        # Perform archiving
        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Create backup
        backup_file = decisions_file.with_suffix(".md.bak")
        shutil.copy2(decisions_file, backup_file)

        # Create archive file
        min_num = min(d['number'] for d in selected_decisions)
        max_num = max(d['number'] for d in selected_decisions)
        archive_content = self._build_archive_content_by_number(selected_decisions, min_num, max_num)
        archive_file.write_text(archive_content, encoding="utf-8")

        # Build list of decisions to keep (all except selected)
        numbers_to_archive_set = set(numbers_to_archive)
        all_decisions = self._parse_decisions(content)
        to_keep = [d for d in all_decisions if d['number'] not in numbers_to_archive_set]

        # Update decisions.md (keep non-archived)
        new_content = self._build_updated_decisions_by_number(to_keep, archive_file_name, min_num, max_num)
        decisions_file.write_text(new_content, encoding="utf-8")

        # Update decisions-index.md
        self._update_decisions_index_by_number(archive_file_name, min_num, max_num)

        console.print(f"\n[green]OK Archived {len(selected_decisions)} decisions to:[/green]")
        console.print(f"  {archive_file}")

        return (archive_file, len(selected_decisions))
