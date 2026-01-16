"""Timeline synchronization between local and Notion."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import time as time_module

from memory_tool.notion.client import NotionClient, NotionError
from memory_tool.utils.config import Config


class TimelineSyncer:
    """Synchronize timeline entries between local .memory/timeline and Notion."""

    def __init__(self, memory_root: Optional[Path] = None):
        """Initialize timeline syncer.

        Args:
            memory_root: Path to .memory directory (auto-detected if None)
        """
        self.memory_root = memory_root or self._find_memory_root()
        self.timeline_dir = self.memory_root / "timeline" / "daily"
        self.config = Config()
        self.client = NotionClient()

        # Entry pattern: "- HH:MM | message"
        self.entry_pattern = re.compile(r"^- (\d{1,2}:\d{2})\s*\|\s*(.+)$", re.MULTILINE)

    def _find_memory_root(self) -> Path:
        """Find .memory directory from current working directory."""
        current = Path.cwd()

        if (current / ".memory").exists():
            return current / ".memory"

        for parent in current.parents:
            if (parent / ".memory").exists():
                return parent / ".memory"

        raise FileNotFoundError(
            "Could not find .memory directory. "
            "Run 'minit' to initialize or navigate to a project with .memory/"
        )

    def _get_local_timezone_str(self) -> str:
        """Get local timezone offset string (e.g., +09:00)."""
        if time_module.daylight and time_module.localtime().tm_isdst > 0:
            utc_offset_sec = -time_module.altzone
        else:
            utc_offset_sec = -time_module.timezone
        utc_offset_hours = utc_offset_sec // 3600
        utc_offset_mins = abs(utc_offset_sec % 3600) // 60
        return f"{utc_offset_hours:+03d}:{utc_offset_mins:02d}"

    def _parse_local_entries(self, date: datetime) -> List[Dict[str, Any]]:
        """Parse timeline entries from local file for a specific date.

        Args:
            date: Date to parse entries for

        Returns:
            List of entry dicts with 'time', 'message', 'datetime'
        """
        year_month = date.strftime("%Y-%m")
        day = date.strftime("%d")
        file_path = self.timeline_dir / year_month / f"{int(day)}.md"

        if not file_path.exists():
            return []

        content = file_path.read_text(encoding="utf-8")
        entries = []

        for match in self.entry_pattern.finditer(content):
            time_str = match.group(1)
            message = match.group(2).strip()

            # Create full datetime
            try:
                time_parts = time_str.split(":")
                entry_dt = date.replace(
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]),
                    second=0,
                    microsecond=0
                )
            except (ValueError, IndexError):
                entry_dt = date

            entries.append({
                "time": time_str,
                "message": message,
                "datetime": entry_dt,
                "raw": match.group(0)
            })

        return entries

    def _parse_notion_entries(self, page_id: str) -> List[Dict[str, Any]]:
        """Parse timeline entries from Notion page.

        Args:
            page_id: Notion page ID

        Returns:
            List of entry dicts with 'time', 'message', 'block_id'
        """
        entries = []

        try:
            response = self.client.client.blocks.children.list(block_id=page_id)

            for block in response.get("results", []):
                if block.get("type") != "paragraph":
                    continue

                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if not rich_text:
                    continue

                # Extract time and message from rich_text
                time_str = None
                message_parts = []
                found_mention = False

                for rt in rich_text:
                    rt_type = rt.get("type")

                    if rt_type == "mention":
                        # Notion date mention
                        mention = rt.get("mention", {})
                        if mention.get("type") == "date":
                            date_info = mention.get("date", {})
                            start = date_info.get("start", "")
                            # Extract time from ISO format (2026-01-16T19:34:00+09:00)
                            if "T" in start:
                                time_part = start.split("T")[1][:5]  # HH:MM
                                time_str = time_part
                                found_mention = True

                    elif rt_type == "text":
                        content = rt.get("text", {}).get("content", "")
                        annotations = rt.get("annotations", {})

                        # Check for bold time format (legacy): "HH:MM | "
                        if annotations.get("bold") and "|" in content and not found_mention:
                            parts = content.split("|")
                            time_str = parts[0].strip()
                            if len(parts) > 1:
                                message_parts.append(parts[1].strip())
                        else:
                            message_parts.append(content)

                if time_str:
                    message = "".join(message_parts).strip()
                    if message:
                        entries.append({
                            "time": time_str,
                            "message": message,
                            "block_id": block.get("id")
                        })

        except Exception as e:
            raise NotionError(f"Failed to parse Notion entries: {e}")

        return entries

    def _entry_key(self, time_str: str, message: str) -> str:
        """Create unique key for an entry."""
        # Normalize time to HH:MM format
        if ":" in time_str:
            parts = time_str.split(":")
            normalized_time = f"{int(parts[0]):02d}:{parts[1]}"
        else:
            normalized_time = time_str
        # Use first 50 chars of message for comparison (handles minor differences)
        return f"{normalized_time}|{message[:50].strip().lower()}"

    def sync(
        self,
        days: int = 1,
        push_only: bool = False,
        pull_only: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Sync timeline entries for specified number of days.

        Args:
            days: Number of days to sync (1 = today only)
            push_only: Only push local to Notion
            pull_only: Only pull Notion to local
            dry_run: Show what would happen without syncing
            verbose: Print verbose output

        Returns:
            Dict with pushed, pulled, skipped, errors counts
        """
        result = {
            "pushed": 0,
            "pulled": 0,
            "skipped": 0,
            "errors": []
        }

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(days):
            date = today - timedelta(days=day_offset)
            date_str = date.strftime("%Y-%m-%d")

            if verbose:
                print(f"[timeline] Processing {date_str}...")

            try:
                day_result = self._sync_day(
                    date=date,
                    push_only=push_only,
                    pull_only=pull_only,
                    dry_run=dry_run,
                    verbose=verbose,
                )

                result["pushed"] += day_result.get("pushed", 0)
                result["pulled"] += day_result.get("pulled", 0)
                result["skipped"] += day_result.get("skipped", 0)
                result["errors"].extend(day_result.get("errors", []))

            except Exception as e:
                result["errors"].append(f"{date_str}: {e}")

        return result

    def _sync_day(
        self,
        date: datetime,
        push_only: bool = False,
        pull_only: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Sync timeline entries for a specific day.

        Args:
            date: Date to sync
            push_only: Only push local to Notion
            pull_only: Only pull Notion to local
            dry_run: Show what would happen without syncing
            verbose: Print verbose output

        Returns:
            Dict with pushed, pulled, skipped, errors counts
        """
        result = {"pushed": 0, "pulled": 0, "skipped": 0, "errors": []}
        date_str = date.strftime("%Y-%m-%d")

        # Get local entries
        local_entries = self._parse_local_entries(date)
        local_keys = {self._entry_key(e["time"], e["message"]): e for e in local_entries}

        # Get or create Notion page
        try:
            page_id = self.client.get_or_create_daily_page(date)
        except NotionError as e:
            result["errors"].append(f"Failed to get Notion page: {e}")
            return result

        # Get Notion entries
        try:
            notion_entries = self._parse_notion_entries(page_id)
        except NotionError as e:
            result["errors"].append(f"Failed to get Notion entries: {e}")
            return result

        notion_keys = {self._entry_key(e["time"], e["message"]): e for e in notion_entries}

        # Push: Local entries not in Notion
        if not pull_only:
            for key, entry in local_keys.items():
                if key not in notion_keys:
                    if dry_run:
                        print(f"  [PUSH] {entry['time']} | {entry['message'][:40]}...")
                        result["pushed"] += 1
                    else:
                        try:
                            self.client.append_timeline_entry(
                                page_id,
                                entry["time"],
                                entry["message"],
                                date_obj=entry["datetime"]
                            )
                            if verbose:
                                print(f"  [PUSH] {entry['time']} | {entry['message'][:40]}...")
                            result["pushed"] += 1
                        except NotionError as e:
                            result["errors"].append(f"Push failed ({entry['time']}): {e}")
                else:
                    result["skipped"] += 1

        # Pull: Notion entries not in local
        if not push_only:
            for key, entry in notion_keys.items():
                if key not in local_keys:
                    if dry_run:
                        print(f"  [PULL] {entry['time']} | {entry['message'][:40]}...")
                        result["pulled"] += 1
                    else:
                        try:
                            self._append_local_entry(date, entry["time"], entry["message"])
                            if verbose:
                                print(f"  [PULL] {entry['time']} | {entry['message'][:40]}...")
                            result["pulled"] += 1
                        except Exception as e:
                            result["errors"].append(f"Pull failed ({entry['time']}): {e}")
                else:
                    if pull_only:
                        result["skipped"] += 1

        return result

    def _append_local_entry(self, date: datetime, time_str: str, message: str):
        """Append an entry to local timeline file.

        Args:
            date: Date for the entry
            time_str: Time string (HH:MM)
            message: Entry message
        """
        year_month = date.strftime("%Y-%m")
        day = date.strftime("%d")
        dir_path = self.timeline_dir / year_month
        file_path = dir_path / f"{int(day)}.md"

        # Ensure directory exists
        dir_path.mkdir(parents=True, exist_ok=True)

        # Create file with header if it doesn't exist
        if not file_path.exists():
            header = f"# {date.strftime('%Y-%m-%d')} Timeline\n"
            file_path.write_text(header, encoding="utf-8")

        # Read existing content
        content = file_path.read_text(encoding="utf-8")

        # Parse existing entries to find correct insertion point (sorted by time)
        existing_entries = []
        for match in self.entry_pattern.finditer(content):
            existing_entries.append({
                "time": match.group(1),
                "message": match.group(2),
                "raw": match.group(0)
            })

        # Add new entry
        new_entry = {"time": time_str, "message": message, "raw": f"- {time_str} | {message}"}

        # Insert in sorted order
        all_entries = existing_entries + [new_entry]
        all_entries.sort(key=lambda e: e["time"])

        # Rebuild file content
        lines = [f"# {date.strftime('%Y-%m-%d')} Timeline"]
        for entry in all_entries:
            lines.append(entry["raw"])

        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def pull_from_notion(
        self,
        date: datetime,
        verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """Pull timeline entries from Notion for a specific date.

        Args:
            date: Date to pull entries for
            verbose: Print verbose output

        Returns:
            List of pulled entries
        """
        try:
            page_id = self.client.get_or_create_daily_page(date)
            return self._parse_notion_entries(page_id)
        except NotionError as e:
            if verbose:
                print(f"Failed to pull from Notion: {e}")
            return []
