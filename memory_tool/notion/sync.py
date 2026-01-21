"""Notion bidirectional sync orchestrator."""

import fnmatch
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

from memory_tool.notion.client import NotionClient, NotionError
from memory_tool.notion.converter import MarkdownNotionConverter
from memory_tool.notion.state import SyncStateManager
from memory_tool.notion.models import (
    SyncConfig,
    SyncTarget,
    SyncAction,
    SyncResult,
    SyncSummary,
    SyncDirection,
    FileSyncState,
    ModuleSyncState,
    ConflictResolution,
)
from memory_tool.utils.config import Config


class NotionSyncError(NotionError):
    """Base exception for sync operations."""
    pass


class ModuleSyncer:
    """Handles bidirectional sync between local modules and Notion."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the syncer.

        Args:
            base_path: Base path for .memory directory. Defaults to cwd.
        """
        self.base_path = base_path or Path.cwd()
        self.memory_path = self.base_path / ".memory"
        self.modules_path = self.memory_path / "modules"

        self.config = Config()
        self.sync_config = self._load_sync_config()

        self.client: Optional[NotionClient] = None
        self.state_manager = SyncStateManager(self.memory_path)
        self.converter = MarkdownNotionConverter()

    def _load_sync_config(self) -> SyncConfig:
        """Load sync configuration from config.yaml."""
        notion_config = self.config.get("notion", {})
        sync_data = notion_config.get("sync", {})
        return SyncConfig.from_dict(sync_data, notion_config)

    def _ensure_client(self):
        """Ensure Notion client is initialized."""
        if self.client is None:
            self.client = NotionClient()

    def get_sync_targets(self) -> List[SyncTarget]:
        """Get list of modules to sync based on configuration.

        Returns:
            List of SyncTarget objects
        """
        targets = []
        seen_paths = set()

        for pattern in self.sync_config.targets:
            # Handle glob patterns
            if "**" in pattern:
                # Recursive match
                base_pattern = pattern.replace("/**", "").replace("**", "")
                if base_pattern:
                    base_dir = self.modules_path / base_pattern
                else:
                    base_dir = self.modules_path

                if base_dir.exists():
                    for module_dir in base_dir.rglob("*"):
                        if module_dir.is_dir() and self._is_module(module_dir):
                            rel_path = module_dir.relative_to(self.modules_path)
                            module_path = str(rel_path).replace("\\", "/")
                            if module_path not in seen_paths:
                                if not self._is_excluded(module_path):
                                    targets.append(SyncTarget(
                                        module_path=module_path,
                                        local_path=str(module_dir),
                                    ))
                                    seen_paths.add(module_path)

            elif "*" in pattern:
                # Single level wildcard
                base_pattern = pattern.replace("/*", "").replace("*", "")
                if base_pattern:
                    base_dir = self.modules_path / base_pattern
                else:
                    base_dir = self.modules_path

                if base_dir.exists():
                    for module_dir in base_dir.iterdir():
                        if module_dir.is_dir() and self._is_module(module_dir):
                            rel_path = module_dir.relative_to(self.modules_path)
                            module_path = str(rel_path).replace("\\", "/")
                            if module_path not in seen_paths:
                                if not self._is_excluded(module_path):
                                    targets.append(SyncTarget(
                                        module_path=module_path,
                                        local_path=str(module_dir),
                                    ))
                                    seen_paths.add(module_path)
            else:
                # Exact path
                module_dir = self.modules_path / pattern
                if module_dir.exists() and self._is_module(module_dir):
                    if pattern not in seen_paths:
                        if not self._is_excluded(pattern):
                            targets.append(SyncTarget(
                                module_path=pattern,
                                local_path=str(module_dir),
                            ))
                            seen_paths.add(pattern)

        return targets

    def _is_module(self, path: Path) -> bool:
        """Check if a directory is a valid module (has .md files)."""
        return any(path.glob("*.md"))

    def _is_excluded(self, module_path: str) -> bool:
        """Check if a module path matches exclusion patterns."""
        for pattern in self.sync_config.exclude_patterns:
            if fnmatch.fnmatch(module_path, pattern):
                return True
        return False

    def sync(
        self,
        module_path: Optional[str] = None,
        push_only: bool = False,
        pull_only: bool = False,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> SyncSummary:
        """Perform bidirectional sync.

        Args:
            module_path: Specific module to sync (None = all configured)
            push_only: Only push local changes to Notion
            pull_only: Only pull Notion changes to local
            force: Force sync regardless of timestamps
            dry_run: Only show what would happen
            verbose: Print progress logs

        Returns:
            SyncSummary with results
        """
        self._ensure_client()
        summary = SyncSummary()

        # Get targets
        if module_path:
            targets = [SyncTarget(
                module_path=module_path,
                local_path=str(self.modules_path / module_path)
            )]
        else:
            targets = self.get_sync_targets()

        if not targets:
            return summary

        if verbose:
            print(f"[sync] Found {len(targets)} target(s) to sync")

        # Sync each target
        for i, target in enumerate(targets, 1):
            if verbose:
                print(f"\n[sync] ({i}/{len(targets)}) Syncing module: {target.module_path}")
            target_summary = self._sync_module(
                target,
                push_only=push_only,
                pull_only=pull_only,
                force=force,
                dry_run=dry_run,
                verbose=verbose,
            )
            for result in target_summary.results:
                summary.add_result(result)

        if not dry_run:
            self.state_manager.update_last_full_sync()

        return summary

    def _sync_module(
        self,
        target: SyncTarget,
        push_only: bool = False,
        pull_only: bool = False,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> SyncSummary:
        """Sync a single module.

        Args:
            target: The sync target
            push_only: Only push
            pull_only: Only pull
            force: Force sync
            dry_run: Dry run mode
            verbose: Print progress logs

        Returns:
            SyncSummary for this module
        """
        summary = SyncSummary()
        module_path = target.module_path
        local_path = Path(target.local_path)

        if not local_path.exists():
            if verbose:
                print(f"  [skip] Local path not found: {local_path}")
            return summary

        # Get module state
        module_state = self.state_manager.get_module_state(module_path)

        # Get or create Notion module page
        if not dry_run:
            if verbose:
                print(f"  [notion] Ensuring module page exists...")
            notion_page_id = self._ensure_module_page(module_path, module_state)
            module_state.notion_page_id = notion_page_id
            if verbose:
                print(f"  [notion] Module page ID: {notion_page_id[:8]}...")
        else:
            notion_page_id = module_state.notion_page_id

        # Get local files
        local_files = self._get_local_files(local_path)
        if verbose:
            print(f"  [local] Found {len(local_files)} file(s)")

        # Get Notion file pages
        notion_files = self._get_notion_file_pages(notion_page_id) if notion_page_id else {}
        if verbose:
            print(f"  [notion] Found {len(notion_files)} existing page(s)")

        # Determine actions for each file
        actions = self._determine_actions(
            module_path,
            local_files,
            notion_files,
            module_state,
            force=force,
        )

        # Execute actions
        action_count = len([a for a in actions if a.direction != SyncDirection.SKIP])
        if verbose and action_count > 0:
            print(f"  [sync] {action_count} file(s) to sync")

        for action in actions:
            if action.direction == SyncDirection.SKIP:
                summary.add_result(SyncResult(
                    success=True,
                    action=action,
                    message="No changes"
                ))
                continue

            if push_only and action.direction == SyncDirection.PULL:
                continue
            if pull_only and action.direction == SyncDirection.PUSH:
                continue

            if verbose:
                direction = "PUSH" if action.direction == SyncDirection.PUSH else "PULL"
                print(f"    [{direction}] {action.file_path}")

            if dry_run:
                summary.add_result(SyncResult(
                    success=True,
                    action=action,
                    message="Would sync"
                ))
            else:
                result = self._execute_action(action, local_path, notion_page_id, module_state)
                summary.add_result(result)
                if verbose:
                    if result.success:
                        print(f"           -> OK")
                    else:
                        print(f"           -> FAIL: {result.message}")

        # Update module page after file syncs
        if not dry_run and notion_page_id:
            if verbose:
                print(f"  [notion] Updating module page...")
            self._update_module_page(module_path, local_path, notion_page_id, module_state)
            module_state.last_sync = datetime.now()
            self.state_manager.set_module_state(module_path, module_state)

        return summary

    def _ensure_module_page(
        self,
        module_path: str,
        module_state: ModuleSyncState
    ) -> str:
        """Ensure module page exists in Notion.

        Args:
            module_path: Module path
            module_state: Current state

        Returns:
            Notion page ID
        """
        if module_state.notion_page_id:
            return module_state.notion_page_id

        # Get root page ID (use module config with built-in legacy fallback)
        root_page_id = self.sync_config.module.root_page_id if self.sync_config.module else None
        if not root_page_id:
            # Additional fallback for legacy configs
            root_page_id = self.sync_config.root_page_id
            if not root_page_id:
                notion_config = self.config.get("notion", {})
                mode = notion_config.get("mode", "default")
                if mode == "pat":
                    root_page_id = notion_config.get("pat", {}).get("default_page_id")
                if not root_page_id:
                    root_page_id = notion_config.get("default_page_id")

        if not root_page_id:
            raise NotionSyncError("No root page ID configured for module sync. Set notion.sync.module.root_page_id in config.yaml")

        # Create hierarchy: root -> ... -> module
        parts = module_path.split("/")
        current_parent = root_page_id

        for i, part in enumerate(parts):
            sub_path = "/".join(parts[:i+1])
            sub_state = self.state_manager.get_module_state(sub_path)

            if sub_state.notion_page_id:
                current_parent = sub_state.notion_page_id
            else:
                # Create or find page (📁 icon for module folders)
                page_id = self.client.get_or_create_subpage(
                    current_parent,
                    part,
                    cache_key=f"module_{sub_path}",
                    icon="📁",
                )
                sub_state.notion_page_id = page_id
                self.state_manager.set_module_state(sub_path, sub_state)
                current_parent = page_id

        return current_parent

    def _get_local_files(self, local_path: Path) -> Dict[str, Path]:
        """Get all .md files in a module directory.

        Args:
            local_path: Module directory path

        Returns:
            Dict of filename -> Path
        """
        files = {}
        for md_file in local_path.glob("*.md"):
            # Skip PLAN files and other special files
            if md_file.name.startswith("PLAN-"):
                continue
            files[md_file.name] = md_file
        return files

    def _get_notion_file_pages(
        self,
        parent_page_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get child pages under a module page.

        Args:
            parent_page_id: Parent page ID

        Returns:
            Dict of filename -> page info
        """
        if not self.client or not parent_page_id:
            return {}

        try:
            response = self.client.client.blocks.children.list(block_id=parent_page_id)
            files = {}

            for block in response.get("results", []):
                if block.get("type") == "child_page":
                    title = block.get("child_page", {}).get("title", "")
                    if title.endswith(".md"):
                        files[title] = {
                            "id": block["id"],
                            "last_edited_time": block.get("last_edited_time"),
                        }

            return files
        except Exception:
            return {}

    def _determine_actions(
        self,
        module_path: str,
        local_files: Dict[str, Path],
        notion_files: Dict[str, Dict[str, Any]],
        module_state: ModuleSyncState,
        force: bool = False,
    ) -> List[SyncAction]:
        """Determine sync actions for each file.

        Args:
            module_path: Module path
            local_files: Local files
            notion_files: Notion file pages
            module_state: Current state
            force: Force sync

        Returns:
            List of SyncAction
        """
        actions = []
        all_files = set(local_files.keys()) | set(notion_files.keys())

        for filename in all_files:
            local_file = local_files.get(filename)
            notion_info = notion_files.get(filename)
            file_state = module_state.files.get(filename, FileSyncState())

            # Get timestamps
            local_mtime = None
            if local_file and local_file.exists():
                local_mtime = datetime.fromtimestamp(local_file.stat().st_mtime)

            notion_edited = None
            if notion_info and notion_info.get("last_edited_time"):
                notion_edited = datetime.fromisoformat(
                    notion_info["last_edited_time"].replace("Z", "+00:00")
                ).replace(tzinfo=None)

            # Determine direction
            if force:
                # Force push if local exists, otherwise skip
                direction = SyncDirection.PUSH if local_mtime else SyncDirection.SKIP
            else:
                direction = self.state_manager.determine_sync_direction(
                    local_mtime,
                    notion_edited,
                    file_state.last_sync,
                    self.sync_config.conflict_resolution,
                )

            actions.append(SyncAction(
                file_path=filename,
                module_path=module_path,
                direction=direction,
                local_mtime=local_mtime,
                notion_edited=notion_edited,
                notion_page_id=notion_info.get("id") if notion_info else None,
            ))

        return actions

    def _execute_action(
        self,
        action: SyncAction,
        local_path: Path,
        parent_page_id: str,
        module_state: ModuleSyncState,
    ) -> SyncResult:
        """Execute a single sync action.

        Args:
            action: The action to execute
            local_path: Local module path
            parent_page_id: Notion parent page ID
            module_state: Module state to update

        Returns:
            SyncResult
        """
        try:
            if action.direction == SyncDirection.PUSH:
                return self._execute_push(action, local_path, parent_page_id, module_state)
            elif action.direction == SyncDirection.PULL:
                return self._execute_pull(action, local_path, module_state)
            else:
                return SyncResult(
                    success=True,
                    action=action,
                    message="Skipped"
                )
        except Exception as e:
            return SyncResult(
                success=False,
                action=action,
                message=str(e),
                error=e,
            )

    def _execute_push(
        self,
        action: SyncAction,
        local_path: Path,
        parent_page_id: str,
        module_state: ModuleSyncState,
    ) -> SyncResult:
        """Push local file to Notion.

        Args:
            action: Push action
            local_path: Local module path
            parent_page_id: Notion parent page ID
            module_state: Module state to update

        Returns:
            SyncResult
        """
        file_path = local_path / action.file_path

        if not file_path.exists():
            return SyncResult(
                success=False,
                action=action,
                message="Local file not found",
            )

        content = file_path.read_text(encoding="utf-8")
        blocks = self.converter.markdown_to_blocks(content)

        if action.notion_page_id:
            # Update existing page
            self._replace_page_content(action.notion_page_id, blocks)
            page_id = action.notion_page_id
        else:
            # Create new page (📄 icon for file pages)
            new_page = self.client.create_page(action.file_path, parent_page_id, icon="📄")
            page_id = new_page["id"]

            # Add content blocks (batch by 100 due to Notion API limit)
            if blocks:
                BATCH_SIZE = 100
                for i in range(0, len(blocks), BATCH_SIZE):
                    batch = blocks[i:i + BATCH_SIZE]
                    self.client.client.blocks.children.append(
                        block_id=page_id,
                        children=batch
                    )

        # Update state
        file_state = module_state.files.get(action.file_path, FileSyncState())
        file_state.notion_page_id = page_id
        file_state.last_sync = datetime.now()
        file_state.local_mtime = action.local_mtime
        module_state.files[action.file_path] = file_state

        return SyncResult(
            success=True,
            action=action,
            message="Pushed to Notion",
        )

    def _execute_pull(
        self,
        action: SyncAction,
        local_path: Path,
        module_state: ModuleSyncState,
    ) -> SyncResult:
        """Pull Notion content to local file.

        Args:
            action: Pull action
            local_path: Local module path
            module_state: Module state to update

        Returns:
            SyncResult
        """
        if not action.notion_page_id:
            return SyncResult(
                success=False,
                action=action,
                message="Notion page not found",
            )

        # Get page content
        blocks = self._get_page_blocks(action.notion_page_id)
        content = self.converter.blocks_to_markdown(blocks)

        # Write to local file
        file_path = local_path / action.file_path
        file_path.write_text(content, encoding="utf-8")

        # Update state
        file_state = module_state.files.get(action.file_path, FileSyncState())
        file_state.notion_page_id = action.notion_page_id
        file_state.last_sync = datetime.now()
        file_state.notion_edited = action.notion_edited
        file_state.local_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        module_state.files[action.file_path] = file_state

        return SyncResult(
            success=True,
            action=action,
            message="Pulled from Notion",
        )

    def _replace_page_content(self, page_id: str, new_blocks: List[Dict[str, Any]]):
        """Replace all content in a Notion page.

        Args:
            page_id: Page ID
            new_blocks: New blocks to set
        """
        # Get existing blocks
        try:
            response = self.client.client.blocks.children.list(block_id=page_id)
            existing_blocks = response.get("results", [])

            # Delete existing blocks (skip child_page blocks)
            for block in existing_blocks:
                if block.get("type") != "child_page":
                    try:
                        self.client.client.blocks.delete(block_id=block["id"])
                    except Exception:
                        pass

            # Add new blocks (batch by 100 due to Notion API limit)
            if new_blocks:
                BATCH_SIZE = 100
                for i in range(0, len(new_blocks), BATCH_SIZE):
                    batch = new_blocks[i:i + BATCH_SIZE]
                    self.client.client.blocks.children.append(
                        block_id=page_id,
                        children=batch
                    )
        except Exception as e:
            raise NotionSyncError(f"Failed to replace page content: {e}")

    def _get_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        """Get all blocks from a Notion page.

        Args:
            page_id: Page ID

        Returns:
            List of block objects
        """
        try:
            response = self.client.client.blocks.children.list(block_id=page_id)
            return response.get("results", [])
        except Exception:
            return []

    def _update_module_page(
        self,
        module_path: str,
        local_path: Path,
        page_id: str,
        module_state: ModuleSyncState,
    ):
        """Update the module page (clear content, keep child pages).

        Args:
            module_path: Module path
            local_path: Local module path
            page_id: Module page ID
            module_state: Module state
        """
        # Just clear old content blocks (child_page blocks are preserved)
        # The module page stays empty - file contents are in child pages
        try:
            response = self.client.client.blocks.children.list(block_id=page_id)
            existing_blocks = response.get("results", [])

            # Delete only non-child_page blocks (paragraphs, etc.)
            for block in existing_blocks:
                if block.get("type") != "child_page":
                    try:
                        self.client.client.blocks.delete(block_id=block["id"])
                    except Exception:
                        pass
        except Exception:
            pass  # Ignore errors when clearing


    def get_status(
        self,
        module_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get sync status for modules.

        Args:
            module_path: Specific module (None = all)

        Returns:
            Status information dict
        """
        self._ensure_client()
        status = {
            "last_full_sync": self.state_manager.get_last_full_sync(),
            "modules": {},
        }

        if module_path:
            targets = [SyncTarget(
                module_path=module_path,
                local_path=str(self.modules_path / module_path)
            )]
        else:
            targets = self.get_sync_targets()

        for target in targets:
            module_status = self._get_module_status(target)
            status["modules"][target.module_path] = module_status

        return status

    def _get_module_status(self, target: SyncTarget) -> Dict[str, Any]:
        """Get status for a single module.

        Args:
            target: Sync target

        Returns:
            Module status dict
        """
        local_path = Path(target.local_path)
        module_state = self.state_manager.get_module_state(target.module_path)

        local_files = self._get_local_files(local_path) if local_path.exists() else {}
        notion_files = self._get_notion_file_pages(module_state.notion_page_id)

        actions = self._determine_actions(
            target.module_path,
            local_files,
            notion_files,
            module_state,
        )

        return {
            "last_sync": module_state.last_sync,
            "notion_page_id": module_state.notion_page_id,
            "to_push": [a.file_path for a in actions if a.direction == SyncDirection.PUSH],
            "to_pull": [a.file_path for a in actions if a.direction == SyncDirection.PULL],
            "in_sync": [a.file_path for a in actions if a.direction == SyncDirection.SKIP],
            "conflicts": [a.file_path for a in actions if a.direction == SyncDirection.CONFLICT],
        }

    def discover_from_notion(
        self,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Discover and pull modules from Notion (when local is empty).

        This method is useful when you have modules in Notion but no local
        .memory/modules directory yet. It will:
        1. List all child pages under root_page_id
        2. Create corresponding local module directories
        3. Download all .md files from Notion

        Args:
            dry_run: If True, only show what would be downloaded
            verbose: If True, show detailed progress

        Returns:
            Dict with discovered modules and results
        """
        self._ensure_client()

        # Get root page ID (use module config with built-in legacy fallback)
        root_page_id = self.sync_config.module.root_page_id if self.sync_config.module else None
        if not root_page_id:
            notion_config = self.config.get("notion", {})
            mode = notion_config.get("mode", "default")
            root_page_id = self.sync_config.root_page_id
            if not root_page_id:
                if mode == "pat":
                    root_page_id = notion_config.get("pat", {}).get("default_page_id")
                if not root_page_id:
                    root_page_id = notion_config.get("default_page_id")

        if not root_page_id:
            raise NotionSyncError("No root page ID configured for module sync. Set notion.sync.module.root_page_id in config.yaml")

        result = {
            "discovered": [],
            "downloaded": [],
            "errors": [],
            "dry_run": dry_run,
        }

        # Discover pages recursively
        discovered_pages = self._discover_pages_recursive(root_page_id, "", verbose)
        result["discovered"] = discovered_pages

        if dry_run:
            return result

        # Ensure modules directory exists
        self.modules_path.mkdir(parents=True, exist_ok=True)

        # Download each discovered module
        for page_info in discovered_pages:
            try:
                module_path = page_info["path"]
                page_id = page_info["id"]

                if verbose:
                    print(f"  Downloading: {module_path}")

                # Create local directory
                local_dir = self.modules_path / module_path
                local_dir.mkdir(parents=True, exist_ok=True)

                # Get file pages under this module
                file_pages = self._get_notion_file_pages(page_id)

                for filename, file_info in file_pages.items():
                    file_page_id = file_info.get("page_id")
                    if file_page_id:
                        # Download content
                        content = self._get_page_markdown(file_page_id)
                        local_file = local_dir / filename
                        local_file.write_text(content, encoding="utf-8")

                        if verbose:
                            print(f"    -> {filename}")

                # Update state
                module_state = ModuleSyncState(
                    notion_page_id=page_id,
                    last_sync=datetime.now().isoformat(),
                )
                self.state_manager.save_module_state(module_path, module_state)

                result["downloaded"].append(module_path)

            except Exception as e:
                result["errors"].append({
                    "module": page_info.get("path", "unknown"),
                    "error": str(e)
                })

        return result

    def _discover_pages_recursive(
        self,
        parent_id: str,
        parent_path: str,
        verbose: bool = False,
        depth: int = 0,
        max_depth: int = 10,
    ) -> List[Dict[str, Any]]:
        """Recursively discover child pages from Notion.

        Args:
            parent_id: Parent page ID
            parent_path: Path prefix for discovered pages
            verbose: Show progress
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            List of discovered page info dicts
        """
        if depth > max_depth:
            return []

        discovered = []

        try:
            # List children of parent page
            response = self.client.client.blocks.children.list(block_id=parent_id)

            for block in response.get("results", []):
                if block.get("type") == "child_page":
                    title = block.get("child_page", {}).get("title", "")
                    page_id = block["id"]

                    # Skip file-like pages (*.md)
                    if title.endswith(".md"):
                        continue

                    # Build path
                    if parent_path:
                        page_path = f"{parent_path}/{title}"
                    else:
                        page_path = title

                    if verbose:
                        print(f"  Found: {page_path}")

                    discovered.append({
                        "id": page_id,
                        "title": title,
                        "path": page_path,
                    })

                    # Recurse into children
                    children = self._discover_pages_recursive(
                        page_id,
                        page_path,
                        verbose,
                        depth + 1,
                        max_depth,
                    )
                    discovered.extend(children)

        except Exception as e:
            if verbose:
                print(f"  Error listing {parent_path}: {e}")

        return discovered

    def _get_page_markdown(self, page_id: str) -> str:
        """Get page content as Markdown.

        Args:
            page_id: Notion page ID

        Returns:
            Markdown content
        """
        try:
            response = self.client.client.blocks.children.list(block_id=page_id)
            blocks = response.get("results", [])
            return self.converter.blocks_to_markdown(blocks)
        except Exception as e:
            raise NotionSyncError(f"Failed to get page content: {e}")
