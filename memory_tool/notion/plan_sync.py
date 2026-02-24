"""Plan synchronization between local and Notion."""

import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any

from memory_tool.notion.client import NotionClient, NotionError
from memory_tool.notion.models import PlanSyncConfig
from memory_tool.utils.config import Config


class PlanSyncer:
    """Synchronize plans between local .memory/plans and Notion.

    Notion page structure:
        Plans Root Page (config: notion.sync.plan.root_page_id)
        ├── Daily Plans/
        │   ├── 2026-01/
        │   │   ├── 21 (2026-01-21)
        │   │   └── 20 (2026-01-20)
        │   └── 2026-02/
        ├── Weekly Plans/
        │   └── 2026/
        │       ├── W04
        │       └── W03
        └── Monthly Plans/
            └── 2026/
                └── 01 (January)
    """

    def __init__(self, memory_root: Optional[Path] = None, backend_config=None):
        """Initialize plan syncer.

        Args:
            memory_root: Path to .memory directory (auto-detected if None)
            backend_config: Optional BackendConfig for secondary backend.
                           If provided, uses that backend's client and plan root_page_id.
        """
        self.memory_root = memory_root or self._find_memory_root()
        self.plans_dir = self.memory_root / "plans"
        self.config = Config()
        self.backend_config = backend_config

        if backend_config and backend_config.client_config is not None:
            self.client = NotionClient(
                backend_config=backend_config.client_config,
                backend_name=backend_config.name,
            )
        else:
            self.client = NotionClient()

        # Get plan sync config using PlanSyncConfig model
        notion_config = self.config.get("notion", {})
        sync_config = notion_config.get("sync", {})
        self.plan_config = PlanSyncConfig.from_dict(sync_config, notion_config)

        # Override root_page_id for secondary backends
        if backend_config and backend_config.role == "secondary":
            sec_root = backend_config.get_plan_root_page_id()
            if sec_root:
                self.plan_config.root_page_id = sec_root

        # Expose config values (for backward compatibility)
        self.enabled = self.plan_config.enabled
        self.root_page_id = self.plan_config.root_page_id
        self.sync_daily = self.plan_config.daily
        self.sync_weekly = self.plan_config.weekly
        self.sync_monthly = self.plan_config.monthly

        # Task pattern: "- [ ] task" or "- [x] task"
        self.task_pattern = re.compile(r"^- \[([ x])\] (.+)$", re.MULTILINE)

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

    def _get_plan_root_page(self, plan_type: str) -> str:
        """Get or create root page for plan type (Daily/Weekly/Monthly Plans).

        Args:
            plan_type: 'daily', 'weekly', or 'monthly'

        Returns:
            Page ID of the root page for this plan type
        """
        if not self.root_page_id:
            raise NotionError(
                "Plan sync root_page_id not configured. "
                "Set 'notion.sync.plan.root_page_id' in config.yaml"
            )

        # Map plan type to folder name and icon
        type_map = {
            "daily": ("Daily Plans", "📅"),
            "weekly": ("Weekly Plans", "📆"),
            "monthly": ("Monthly Plans", "📆"),
        }

        folder_name, icon = type_map.get(plan_type, (f"{plan_type.title()} Plans", "📋"))
        cache_key = f"plan_root_{plan_type}"

        return self.client.get_or_create_subpage(
            self.root_page_id, folder_name, cache_key, icon=icon
        )

    def _get_daily_plan_page(self, target_date: date) -> str:
        """Get or create Notion page for daily plan.

        Structure: Daily Plans / YYYY-MM / DD

        Args:
            target_date: Date of the plan

        Returns:
            Page ID
        """
        root_id = self._get_plan_root_page("daily")

        # Month folder (e.g., "2026-01")
        month_str = target_date.strftime("%Y-%m")
        month_cache_key = f"plan_daily_month_{month_str}"
        month_id = self.client.get_or_create_subpage(root_id, month_str, month_cache_key)

        # Day page (e.g., "21")
        day_str = str(target_date.day)
        day_cache_key = f"plan_daily_{target_date.strftime('%Y-%m-%d')}"
        day_id = self.client.get_or_create_subpage(month_id, day_str, day_cache_key)

        return day_id

    def _get_weekly_plan_page(self, target_date: date) -> str:
        """Get or create Notion page for weekly plan.

        Structure: Weekly Plans / YYYY / W##

        Args:
            target_date: Any date within the target week

        Returns:
            Page ID
        """
        root_id = self._get_plan_root_page("weekly")

        # Get week info
        iso_cal = target_date.isocalendar()
        year = iso_cal[0]
        week = iso_cal[1]

        # Year folder
        year_str = str(year)
        year_cache_key = f"plan_weekly_year_{year}"
        year_id = self.client.get_or_create_subpage(root_id, year_str, year_cache_key)

        # Week page (e.g., "W04")
        week_str = f"W{week:02d}"
        week_cache_key = f"plan_weekly_{year}_W{week:02d}"
        week_id = self.client.get_or_create_subpage(year_id, week_str, week_cache_key)

        return week_id

    def _get_monthly_plan_page(self, target_date: date) -> str:
        """Get or create Notion page for monthly plan.

        Structure: Monthly Plans / YYYY / MM (Month Name)

        Args:
            target_date: Any date within the target month

        Returns:
            Page ID
        """
        root_id = self._get_plan_root_page("monthly")

        # Year folder
        year_str = str(target_date.year)
        year_cache_key = f"plan_monthly_year_{target_date.year}"
        year_id = self.client.get_or_create_subpage(root_id, year_str, year_cache_key)

        # Month page (e.g., "01 (January)")
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_str = f"{target_date.month:02d} ({month_names[target_date.month - 1]})"
        month_cache_key = f"plan_monthly_{target_date.year}_{target_date.month:02d}"
        month_id = self.client.get_or_create_subpage(year_id, month_str, month_cache_key)

        return month_id

    def _parse_local_tasks(self, content: str) -> List[Dict[str, Any]]:
        """Parse tasks from local plan content.

        Args:
            content: Plan markdown content

        Returns:
            List of task dicts with 'text', 'completed', 'raw'
        """
        tasks = []
        for match in self.task_pattern.finditer(content):
            completed = match.group(1) == "x"
            text = match.group(2).strip()
            # Remove timestamp suffix if present
            text = re.sub(r'\s*\[\d{1,2}:\d{2}\]$', '', text)
            tasks.append({
                "text": text,
                "completed": completed,
                "raw": match.group(0)
            })
        return tasks

    def _parse_notion_tasks(self, page_id: str) -> List[Dict[str, Any]]:
        """Parse tasks from Notion page (to_do blocks).

        Args:
            page_id: Notion page ID

        Returns:
            List of task dicts with 'text', 'completed', 'block_id'
        """
        tasks = []

        try:
            response = self.client.client.blocks.children.list(block_id=page_id)

            for block in response.get("results", []):
                if block.get("type") != "to_do":
                    continue

                to_do = block.get("to_do", {})
                rich_text = to_do.get("rich_text", [])
                checked = to_do.get("checked", False)

                text_parts = []
                for rt in rich_text:
                    if rt.get("type") == "text":
                        text_parts.append(rt.get("text", {}).get("content", ""))

                text = "".join(text_parts).strip()
                if text:
                    tasks.append({
                        "text": text,
                        "completed": checked,
                        "block_id": block.get("id")
                    })

        except Exception as e:
            raise NotionError(f"Failed to parse Notion tasks: {e}")

        return tasks

    def _task_key(self, text: str) -> str:
        """Create unique key for a task."""
        # Use first 50 chars of text for comparison
        return text[:50].strip().lower()

    def _append_notion_task(self, page_id: str, text: str, completed: bool = False):
        """Append a to_do block to Notion page.

        Args:
            page_id: Notion page ID
            text: Task text
            completed: Whether task is completed
        """
        self.client.client.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": text}
                            }
                        ],
                        "checked": completed
                    }
                }
            ]
        )

    def _update_notion_task(self, block_id: str, completed: bool):
        """Update completion status of a Notion to_do block.

        Args:
            block_id: Notion block ID
            completed: New completion status
        """
        self.client.client.blocks.update(
            block_id=block_id,
            to_do={"checked": completed}
        )

    def sync(
        self,
        plan_type: str = "all",
        days: int = 7,
        push_only: bool = False,
        pull_only: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Sync plans between local and Notion.

        Args:
            plan_type: 'daily', 'weekly', 'monthly', or 'all'
            days: Number of days to sync for daily plans
            push_only: Only push local to Notion
            pull_only: Only pull Notion to local
            dry_run: Show what would happen without syncing
            verbose: Print verbose output

        Returns:
            Dict with pushed, pulled, updated, skipped, errors counts
        """
        if not self.enabled:
            return {
                "pushed": 0,
                "pulled": 0,
                "updated": 0,
                "skipped": 0,
                "errors": ["Plan sync not enabled in config"]
            }

        result = {
            "pushed": 0,
            "pulled": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }

        today = date.today()

        # Sync daily plans
        if plan_type in ("all", "daily") and self.sync_daily:
            for day_offset in range(days):
                target_date = today - timedelta(days=day_offset)
                try:
                    day_result = self._sync_daily_plan(
                        target_date, push_only, pull_only, dry_run, verbose
                    )
                    result["pushed"] += day_result.get("pushed", 0)
                    result["pulled"] += day_result.get("pulled", 0)
                    result["updated"] += day_result.get("updated", 0)
                    result["skipped"] += day_result.get("skipped", 0)
                    result["errors"].extend(day_result.get("errors", []))
                except Exception as e:
                    result["errors"].append(f"Daily {target_date}: {e}")

        # Sync weekly plans
        if plan_type in ("all", "weekly") and self.sync_weekly:
            # Sync this week and last week
            for week_offset in range(2):
                target_date = today - timedelta(weeks=week_offset)
                try:
                    week_result = self._sync_weekly_plan(
                        target_date, push_only, pull_only, dry_run, verbose
                    )
                    result["pushed"] += week_result.get("pushed", 0)
                    result["pulled"] += week_result.get("pulled", 0)
                    result["updated"] += week_result.get("updated", 0)
                    result["skipped"] += week_result.get("skipped", 0)
                    result["errors"].extend(week_result.get("errors", []))
                except Exception as e:
                    iso_cal = target_date.isocalendar()
                    result["errors"].append(f"Weekly W{iso_cal[1]:02d}: {e}")

        # Sync monthly plans
        if plan_type in ("all", "monthly") and self.sync_monthly:
            # Sync this month
            try:
                month_result = self._sync_monthly_plan(
                    today, push_only, pull_only, dry_run, verbose
                )
                result["pushed"] += month_result.get("pushed", 0)
                result["pulled"] += month_result.get("pulled", 0)
                result["updated"] += month_result.get("updated", 0)
                result["skipped"] += month_result.get("skipped", 0)
                result["errors"].extend(month_result.get("errors", []))
            except Exception as e:
                result["errors"].append(f"Monthly {today.strftime('%Y-%m')}: {e}")

        return result

    def _sync_daily_plan(
        self,
        target_date: date,
        push_only: bool = False,
        pull_only: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Sync daily plan for specific date."""
        result = {"pushed": 0, "pulled": 0, "updated": 0, "skipped": 0, "errors": []}
        date_str = target_date.strftime("%Y-%m-%d")

        # Get local plan path
        year_month = target_date.strftime("%Y-%m")
        day = target_date.strftime("%d")
        local_path = self.plans_dir / "daily" / year_month / f"{day}.md"

        if verbose:
            print(f"[plan:daily] Processing {date_str}...")

        # Read local tasks
        local_tasks = []
        if local_path.exists():
            content = local_path.read_text(encoding="utf-8")
            local_tasks = self._parse_local_tasks(content)

        local_keys = {self._task_key(t["text"]): t for t in local_tasks}

        # Get Notion tasks
        try:
            page_id = self._get_daily_plan_page(target_date)
            notion_tasks = self._parse_notion_tasks(page_id)
        except NotionError as e:
            result["errors"].append(f"Failed to get Notion page: {e}")
            return result

        notion_keys = {self._task_key(t["text"]): t for t in notion_tasks}

        # Push: Local tasks not in Notion
        if not pull_only:
            for key, task in local_keys.items():
                if key not in notion_keys:
                    if dry_run:
                        print(f"  [PUSH] {task['text'][:50]}...")
                        result["pushed"] += 1
                    else:
                        try:
                            self._append_notion_task(page_id, task["text"], task["completed"])
                            if verbose:
                                print(f"  [PUSH] {task['text'][:50]}...")
                            result["pushed"] += 1
                        except Exception as e:
                            result["errors"].append(f"Push failed: {e}")
                else:
                    # Check if completion status differs
                    notion_task = notion_keys[key]
                    if task["completed"] != notion_task["completed"]:
                        if dry_run:
                            status = "completed" if task["completed"] else "uncompleted"
                            print(f"  [UPDATE] {task['text'][:40]}... -> {status}")
                            result["updated"] += 1
                        else:
                            try:
                                self._update_notion_task(notion_task["block_id"], task["completed"])
                                if verbose:
                                    status = "completed" if task["completed"] else "uncompleted"
                                    print(f"  [UPDATE] {task['text'][:40]}... -> {status}")
                                result["updated"] += 1
                            except Exception as e:
                                result["errors"].append(f"Update failed: {e}")
                    else:
                        result["skipped"] += 1

        # Pull: Notion tasks not in local
        if not push_only:
            for key, task in notion_keys.items():
                if key not in local_keys:
                    if dry_run:
                        print(f"  [PULL] {task['text'][:50]}...")
                        result["pulled"] += 1
                    else:
                        try:
                            self._append_local_task(local_path, task["text"], task["completed"])
                            if verbose:
                                print(f"  [PULL] {task['text'][:50]}...")
                            result["pulled"] += 1
                        except Exception as e:
                            result["errors"].append(f"Pull failed: {e}")
                elif pull_only:
                    result["skipped"] += 1

        return result

    def _sync_weekly_plan(
        self,
        target_date: date,
        push_only: bool = False,
        pull_only: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Sync weekly plan for specific week."""
        result = {"pushed": 0, "pulled": 0, "updated": 0, "skipped": 0, "errors": []}

        iso_cal = target_date.isocalendar()
        year = iso_cal[0]
        week = iso_cal[1]
        week_str = f"W{week:02d}"

        # Get local plan path
        local_path = self.plans_dir / "weekly" / str(year) / f"{week_str}.md"

        if verbose:
            print(f"[plan:weekly] Processing {year} {week_str}...")

        # Read local tasks
        local_tasks = []
        if local_path.exists():
            content = local_path.read_text(encoding="utf-8")
            local_tasks = self._parse_local_tasks(content)

        local_keys = {self._task_key(t["text"]): t for t in local_tasks}

        # Get Notion tasks
        try:
            page_id = self._get_weekly_plan_page(target_date)
            notion_tasks = self._parse_notion_tasks(page_id)
        except NotionError as e:
            result["errors"].append(f"Failed to get Notion page: {e}")
            return result

        notion_keys = {self._task_key(t["text"]): t for t in notion_tasks}

        # Push: Local tasks not in Notion
        if not pull_only:
            for key, task in local_keys.items():
                if key not in notion_keys:
                    if dry_run:
                        print(f"  [PUSH] {task['text'][:50]}...")
                        result["pushed"] += 1
                    else:
                        try:
                            self._append_notion_task(page_id, task["text"], task["completed"])
                            if verbose:
                                print(f"  [PUSH] {task['text'][:50]}...")
                            result["pushed"] += 1
                        except Exception as e:
                            result["errors"].append(f"Push failed: {e}")
                else:
                    notion_task = notion_keys[key]
                    if task["completed"] != notion_task["completed"]:
                        if dry_run:
                            status = "completed" if task["completed"] else "uncompleted"
                            print(f"  [UPDATE] {task['text'][:40]}... -> {status}")
                            result["updated"] += 1
                        else:
                            try:
                                self._update_notion_task(notion_task["block_id"], task["completed"])
                                if verbose:
                                    status = "completed" if task["completed"] else "uncompleted"
                                    print(f"  [UPDATE] {task['text'][:40]}... -> {status}")
                                result["updated"] += 1
                            except Exception as e:
                                result["errors"].append(f"Update failed: {e}")
                    else:
                        result["skipped"] += 1

        # Pull: Notion tasks not in local
        if not push_only:
            for key, task in notion_keys.items():
                if key not in local_keys:
                    if dry_run:
                        print(f"  [PULL] {task['text'][:50]}...")
                        result["pulled"] += 1
                    else:
                        try:
                            self._append_local_task(local_path, task["text"], task["completed"])
                            if verbose:
                                print(f"  [PULL] {task['text'][:50]}...")
                            result["pulled"] += 1
                        except Exception as e:
                            result["errors"].append(f"Pull failed: {e}")
                elif pull_only:
                    result["skipped"] += 1

        return result

    def _sync_monthly_plan(
        self,
        target_date: date,
        push_only: bool = False,
        pull_only: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Sync monthly plan for specific month."""
        result = {"pushed": 0, "pulled": 0, "updated": 0, "skipped": 0, "errors": []}

        year_month = target_date.strftime("%Y-%m")

        # Get local plan path
        local_path = self.plans_dir / "monthly" / str(target_date.year) / f"{target_date.month:02d}.md"

        if verbose:
            print(f"[plan:monthly] Processing {year_month}...")

        # Read local tasks
        local_tasks = []
        if local_path.exists():
            content = local_path.read_text(encoding="utf-8")
            local_tasks = self._parse_local_tasks(content)

        local_keys = {self._task_key(t["text"]): t for t in local_tasks}

        # Get Notion tasks
        try:
            page_id = self._get_monthly_plan_page(target_date)
            notion_tasks = self._parse_notion_tasks(page_id)
        except NotionError as e:
            result["errors"].append(f"Failed to get Notion page: {e}")
            return result

        notion_keys = {self._task_key(t["text"]): t for t in notion_tasks}

        # Push: Local tasks not in Notion
        if not pull_only:
            for key, task in local_keys.items():
                if key not in notion_keys:
                    if dry_run:
                        print(f"  [PUSH] {task['text'][:50]}...")
                        result["pushed"] += 1
                    else:
                        try:
                            self._append_notion_task(page_id, task["text"], task["completed"])
                            if verbose:
                                print(f"  [PUSH] {task['text'][:50]}...")
                            result["pushed"] += 1
                        except Exception as e:
                            result["errors"].append(f"Push failed: {e}")
                else:
                    notion_task = notion_keys[key]
                    if task["completed"] != notion_task["completed"]:
                        if dry_run:
                            status = "completed" if task["completed"] else "uncompleted"
                            print(f"  [UPDATE] {task['text'][:40]}... -> {status}")
                            result["updated"] += 1
                        else:
                            try:
                                self._update_notion_task(notion_task["block_id"], task["completed"])
                                if verbose:
                                    status = "completed" if task["completed"] else "uncompleted"
                                    print(f"  [UPDATE] {task['text'][:40]}... -> {status}")
                                result["updated"] += 1
                            except Exception as e:
                                result["errors"].append(f"Update failed: {e}")
                    else:
                        result["skipped"] += 1

        # Pull: Notion tasks not in local
        if not push_only:
            for key, task in notion_keys.items():
                if key not in local_keys:
                    if dry_run:
                        print(f"  [PULL] {task['text'][:50]}...")
                        result["pulled"] += 1
                    else:
                        try:
                            self._append_local_task(local_path, task["text"], task["completed"])
                            if verbose:
                                print(f"  [PULL] {task['text'][:50]}...")
                            result["pulled"] += 1
                        except Exception as e:
                            result["errors"].append(f"Pull failed: {e}")
                elif pull_only:
                    result["skipped"] += 1

        return result

    def _append_local_task(self, file_path: Path, text: str, completed: bool = False):
        """Append a task to local plan file.

        Args:
            file_path: Path to plan file
            text: Task text
            completed: Whether task is completed
        """
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file with header if it doesn't exist
        if not file_path.exists():
            # Determine plan type from path
            if "daily" in str(file_path):
                header = f"# Daily Plan\n\n## Today's Goals\n\n"
            elif "weekly" in str(file_path):
                header = f"# Weekly Plan\n\n## Weekly Goals\n\n"
            elif "monthly" in str(file_path):
                header = f"# Monthly Plan\n\n## Monthly Goals\n\n"
            else:
                header = f"# Plan\n\n## Goals\n\n"
            file_path.write_text(header, encoding="utf-8")

        # Read existing content
        content = file_path.read_text(encoding="utf-8")

        # Add task
        check = "x" if completed else " "
        task_line = f"- [{check}] {text}"

        # Find the goals section and append
        if "## " in content:
            # Find first section and append after it
            lines = content.split("\n")
            insert_idx = None
            for i, line in enumerate(lines):
                if line.startswith("## "):
                    insert_idx = i + 1
                    break

            if insert_idx:
                # Skip empty lines after header
                while insert_idx < len(lines) and not lines[insert_idx].strip():
                    insert_idx += 1
                lines.insert(insert_idx, task_line)
                content = "\n".join(lines)
            else:
                content += f"\n{task_line}"
        else:
            content += f"\n{task_line}"

        file_path.write_text(content, encoding="utf-8")

    def get_status(self) -> Dict[str, Any]:
        """Get sync status for plans.

        Returns:
            Dict with status information
        """
        status = {
            "enabled": self.enabled,
            "root_page_id": self.root_page_id,
            "sync_daily": self.sync_daily,
            "sync_weekly": self.sync_weekly,
            "sync_monthly": self.sync_monthly,
        }

        if not self.enabled:
            status["message"] = "Plan sync not enabled"
        elif not self.root_page_id:
            status["message"] = "Plan sync root_page_id not configured"
        else:
            status["message"] = "Ready"

        return status
