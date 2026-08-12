"""Module management functionality."""

import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class ModuleError(Exception):
    """Base exception for module operations."""
    pass


class ModuleManager:
    """Manager for memory modules."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize module manager.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.modules_path = self.memory_path / "modules"
        self.archive_path = self.modules_path / "archive"

    def is_initialized(self) -> bool:
        """Check if .memory/modules/ exists."""
        return self.modules_path.exists()

    def _validate_module_name(self, name: str) -> None:
        """Validate module name or path."""
        parts = name.split('/')
        reserved = ["archive", "templates", ".git"]

        for part in parts:
            if not part:
                raise ModuleError(f"Invalid module path: {name}. Empty path component.")

            if not re.match(r'^[\w\s-]+$', part):
                raise ModuleError(
                    f"Invalid module path component: {part}. "
                    f"Use only letters, numbers, spaces, dashes, and underscores."
                )

            if part.lower() in reserved:
                raise ModuleError(f"Reserved name in path: {part}")

    def get_module_file_path(self, name: str) -> Path:
        """Get file path for a module."""
        return self.modules_path / f"{name}.md"

    def module_exists(self, name: str) -> bool:
        """Check if module exists (as single file or old directory format)."""
        file_path = self.get_module_file_path(name)
        if file_path.exists() and file_path.is_file():
            return True
        # Check for legacy directory format
        dir_path = self.modules_path / name
        return dir_path.exists() and dir_path.is_dir() and (dir_path / "module.md").exists() or (dir_path / "current.md").exists()

    def is_archived(self, name: str) -> bool:
        """Check if module is archived."""
        if not self.archive_path.exists():
            return False

        archive_module_file = self.archive_path / f"{name}.md"
        archive_module_dir = self.archive_path / name
        return (archive_module_file.exists() and archive_module_file.is_file()) or (archive_module_dir.exists() and archive_module_dir.is_dir())

    def create(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Path:
        """Create new single-file module structure.

        Args:
            name: Module name or path (e.g. 'memory-tool' or 'memory-tool/core-system')
            description: Module description
            tags: Module tags

        Returns:
            Path to created single markdown file

        Raises:
            ModuleError: If creation fails
        """
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        self._validate_module_name(name)

        if self.module_exists(name):
            raise ModuleError(f"Module already exists: {name}")

        file_path = self.get_module_file_path(name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d")
        tags_str = ", ".join(tags) if tags else ""
        desc_str = description if description else "TODO: Describe the purpose of this module"

        content = f"""# Module: {name}

**Created:** {timestamp}
**Tags:** {tags_str}

## Overview

### Purpose
{desc_str}

### Scope
TODO: Define what is included and excluded from this module

### Architecture
TODO: Describe high-level architecture and design decisions

## Current Status

### In Progress
- [ ] TODO: Add current tasks

### Completed
- [x] Module created

### Blocked
None

### Next Steps
1. TODO: Define next actions

## Decisions

### Decision 1: Module Creation ({timestamp})
**Context:** Initial module setup
**Decision:** Created {name} module
**Rationale:** {desc_str}
**Status:** Accepted

## Dependencies

### Internal Dependencies
None yet

### External Dependencies
None yet

### Dependents
None yet

## Interface

### Public API
TODO: Document public interfaces, commands, or APIs

### Data Structures
TODO: Document key data structures
"""

        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise ModuleError(f"Failed to create module file: {e}")

        return file_path

    def discover_all_modules(self) -> List[Path]:
        """Discover all modules recursively by finding .md files and legacy dirs.

        Returns:
            List of module relative paths (without .md extension) sorted by path.
        """
        if not self.modules_path.exists():
            return []

        modules = set()

        # 1. Discover single-file modules (.md)
        for md_file in self.modules_path.rglob("*.md"):
            # Skip archive directory
            if "archive" in md_file.parts:
                continue
            # Skip uppercase meta summary files or index files starting with _ or uppercase special files
            if md_file.name.startswith("_") or md_file.name.isupper() or md_file.name in ["MIGRATION-SUMMARY.md"]:
                continue
            # Skip legacy files inside old module directories (module.md, current.md, etc.) if parent is legacy module
            if md_file.name in ["module.md", "current.md", "decisions.md", "dependencies.md", "interface.md"]:
                # Check if it's legacy module directory
                legacy_dir = md_file.parent
                try:
                    rel_legacy = legacy_dir.relative_to(self.modules_path)
                    modules.add(rel_legacy)
                except ValueError:
                    pass
                continue

            try:
                rel_path = md_file.relative_to(self.modules_path)
                # Remove .md suffix
                module_name_path = rel_path.with_suffix("")
                modules.add(module_name_path)
            except ValueError:
                continue

        result = list(modules)
        result.sort(key=lambda p: str(p))
        return result

    def find_module_by_name(self, name: str, exact: bool = False) -> List[str]:
        """Find module(s) by name, searching all module paths."""
        all_modules = self.discover_all_modules()
        matches = []

        for module_path in all_modules:
            module_str = str(module_path)
            module_parts = module_path.parts

            if exact:
                if module_str == name:
                    matches.append(module_str)
            else:
                if module_str == name or module_parts[-1] == name:
                    matches.append(module_str)

        return matches

    def list_modules(self, include_archived: bool = False) -> Dict[str, List[str]]:
        """List all modules."""
        result = {"active": []}

        if not self.modules_path.exists():
            return result

        discovered = self.discover_all_modules()
        result["active"] = [str(p) for p in discovered]

        if include_archived and self.archive_path.exists():
            archived = []
            for item in self.archive_path.rglob("*"):
                if "archive" in item.parts:
                    if item.is_file() and item.suffix == ".md" and not item.name.startswith("_"):
                        rel = item.relative_to(self.archive_path).with_suffix("")
                        archived.append(str(rel))
                    elif item.is_dir() and not item.name.startswith("."):
                        if (item / "module.md").exists() or (item / "current.md").exists():
                            rel = item.relative_to(self.archive_path)
                            archived.append(str(rel))
            archived = list(set(archived))
            archived.sort()
            result["archived"] = archived

        return result

    def build_module_tree(self) -> Dict:
        """Build hierarchical tree structure of modules."""
        modules = self.discover_all_modules()
        tree = {}

        for module_path in modules:
            parts = module_path.parts
            current = tree

            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        return tree

    def get_module_info(self, name: str) -> Dict:
        """Get information about a module."""
        file_path = self.get_module_file_path(name)
        legacy_dir = self.modules_path / name

        exists = file_path.exists() or (legacy_dir.exists() and legacy_dir.is_dir())
        if not exists:
            raise ModuleError(f"Module not found: {name}")

        rel_path = Path(name)
        parent = str(rel_path.parent) if rel_path.parent != Path(".") else None

        all_modules = self.discover_all_modules()
        children = []
        for mod in all_modules:
            mod_str = str(mod)
            if mod_str != name and mod_str.startswith(f"{name}/"):
                # Direct child check
                sub = mod_str[len(name) + 1:]
                if "/" not in sub:
                    children.append(mod_str)

        children.sort()

        return {
            "name": name,
            "path": file_path if file_path.exists() else legacy_dir,
            "parent": parent,
            "children": children,
        }

    def migrate_module(self, name_or_path: str) -> Path:
        """Migrate a legacy multi-file module directory into a single markdown file.

        Args:
            name_or_path: Module relative path (e.g. 'memory-tool/core-system')

        Returns:
            Path to newly created single module markdown file (.md)
        """
        dir_path = self.modules_path / name_or_path
        if not dir_path.exists() or not dir_path.is_dir():
            # Check if it's already a single file
            file_path = self.get_module_file_path(name_or_path)
            if file_path.exists():
                return file_path
            raise ModuleError(f"Legacy module directory not found: {name_or_path}")

        # Files to combine in standard order
        std_files = ["module.md", "current.md", "decisions.md", "dependencies.md", "interface.md"]
        combined_sections = []

        # Read module.md first or create header
        module_md_path = dir_path / "module.md"
        if module_md_path.exists():
            combined_sections.append(module_md_path.read_text(encoding="utf-8").strip())
        else:
            combined_sections.append(f"# Module: {Path(name_or_path).name}\n")

        # Section mapping for other standard files
        section_titles = {
            "current.md": "## Current Status",
            "decisions.md": "## Decisions",
            "dependencies.md": "## Dependencies",
            "interface.md": "## Interface",
        }

        for fname, default_title in section_titles.items():
            fpath = dir_path / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8").strip()
                # Avoid duplicate title if already present in content
                if not content.startswith("#"):
                    content = f"{default_title}\n\n{content}"
                combined_sections.append(content)

        # Catch any additional non-standard .md files in legacy directory (not subdirectories)
        for extra_file in dir_path.iterdir():
            if extra_file.is_file() and extra_file.suffix == ".md" and extra_file.name not in std_files:
                content = extra_file.read_text(encoding="utf-8").strip()
                combined_sections.append(f"## {extra_file.stem.capitalize()}\n\n{content}")

        combined_content = "\n\n---\n\n".join(combined_sections) + "\n"

        target_file = self.get_module_file_path(name_or_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(combined_content, encoding="utf-8")

        # Clean up legacy standard files
        for fname in std_files:
            fpath = dir_path / fname
            if fpath.exists():
                fpath.unlink()

        # Remove empty legacy directory if no subdirectories/submodules remain
        remaining_items = list(dir_path.iterdir())
        if not remaining_items:
            dir_path.rmdir()

        return target_file

    def migrate_all_modules(self) -> List[Path]:
        """Find and migrate all legacy multi-file module directories into single files.

        Returns:
            List of created/migrated single module .md file paths.
        """
        migrated = []
        if not self.modules_path.exists():
            return migrated

        # Find all legacy directories containing module.md or current.md
        legacy_dirs = []
        for current_file in list(self.modules_path.rglob("current.md")) + list(self.modules_path.rglob("module.md")):
            d = current_file.parent
            if "archive" not in d.parts and d not in legacy_dirs:
                legacy_dirs.append(d)

        # Sort deeper directories first so submodules are migrated before parent directories
        legacy_dirs.sort(key=lambda p: len(p.parts), reverse=True)

        for d in legacy_dirs:
            try:
                rel = d.relative_to(self.modules_path)
                mpath = self.migrate_module(str(rel))
                migrated.append(mpath)
            except Exception as e:
                print(f"Warning: Failed to migrate {d}: {e}")

        return migrated

    def archive(self, name: str, reason: str = "") -> Path:
        """Archive a module."""
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        file_path = self.get_module_file_path(name)
        dir_path = self.modules_path / name

        if not file_path.exists() and not dir_path.exists():
            raise ModuleError(f"Module not found: {name}")

        if self.is_archived(name):
            raise ModuleError(f"Module already archived: {name}")

        self.archive_path.mkdir(parents=True, exist_ok=True)
        import shutil

        target_archive = self.archive_path / f"{name}.md"
        target_archive.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            shutil.move(str(file_path), str(target_archive))
        elif dir_path.exists():
            shutil.move(str(dir_path), str(self.archive_path / name))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        index_path = self.archive_path / "_index.md"

        if index_path.exists():
            index_content = index_path.read_text(encoding="utf-8")
        else:
            index_content = "# Archived Modules\n\n"

        new_entry = f"""## {name}
- **Archived:** {timestamp}
- **Reason:** {reason if reason else "No reason specified"}
- **Location:** ./{name}.md

"""
        index_content += new_entry
        index_path.write_text(index_content, encoding="utf-8")

        return target_archive

    def unarchive(self, name: str) -> Path:
        """Restore module from archive."""
        if not self.archive_path.exists():
            raise ModuleError("Archive directory not found")

        archive_file = self.archive_path / f"{name}.md"
        archive_dir = self.archive_path / name

        if not archive_file.exists() and not archive_dir.exists():
            raise ModuleError(f"Module not found in archive: {name}")

        if self.module_exists(name):
            raise ModuleError(
                f"Active module with name '{name}' already exists. Archive or rename it first."
            )

        import shutil
        file_path = self.get_module_file_path(name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if archive_file.exists():
            shutil.move(str(archive_file), str(file_path))
            res = file_path
        else:
            shutil.move(str(archive_dir), str(self.modules_path / name))
            res = self.modules_path / name

        return res

    def rename(self, old_name: str, new_name: str) -> Path:
        """Rename a module."""
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        self._validate_module_name(new_name)

        old_file = self.get_module_file_path(old_name)
        old_dir = self.modules_path / old_name

        if not old_file.exists() and not old_dir.exists():
            raise ModuleError(f"Module not found: {old_name}")

        if self.module_exists(new_name):
            raise ModuleError(f"Module already exists: {new_name}")

        import shutil
        new_file = self.get_module_file_path(new_name)
        new_file.parent.mkdir(parents=True, exist_ok=True)

        if old_file.exists():
            shutil.move(str(old_file), str(new_file))
            try:
                content = new_file.read_text(encoding="utf-8")
                old_base = Path(old_name).name
                new_base = Path(new_name).name
                content = content.replace(f"# Module: {old_base}", f"# Module: {new_base}")
                content = content.replace(f"# Module: {old_name}", f"# Module: {new_name}")
                new_file.write_text(content, encoding="utf-8")
            except Exception:
                pass
            return new_file
        else:
            shutil.move(str(old_dir), str(self.modules_path / new_name))
            return self.modules_path / new_name

