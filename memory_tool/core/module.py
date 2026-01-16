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
        """Check if .memory/modules/ exists.

        Returns:
            True if modules directory exists
        """
        return self.modules_path.exists()

    def _validate_module_name(self, name: str) -> None:
        """Validate module name or path.

        Args:
            name: Module name or path to validate (e.g., 'module' or 'projects/website')

        Raises:
            ModuleError: If name is invalid
        """
        # Split path components
        parts = name.split('/')

        # Check for reserved names
        reserved = ["archive", "templates", ".git"]

        # Validate each path component
        for part in parts:
            if not part:
                raise ModuleError(f"Invalid module path: {name}. Empty path component.")

            # Check for valid characters (word characters including Unicode, space, dash)
            # \w matches alphanumeric + underscore + Unicode letters (Korean, Japanese, etc.)
            # \s allows spaces in module names
            if not re.match(r'^[\w\s-]+$', part):
                raise ModuleError(
                    f"Invalid module path component: {part}. "
                    f"Use only letters, numbers, spaces, dashes, and underscores."
                )

            # Check for reserved names
            if part.lower() in reserved:
                raise ModuleError(f"Reserved name in path: {part}")

    def module_exists(self, name: str) -> bool:
        """Check if module exists.

        Args:
            name: Module name

        Returns:
            True if module exists
        """
        module_path = self.modules_path / name
        return module_path.exists() and module_path.is_dir()

    def is_archived(self, name: str) -> bool:
        """Check if module is archived.

        Args:
            name: Module name

        Returns:
            True if module is in archive
        """
        if not self.archive_path.exists():
            return False

        archive_module_path = self.archive_path / name
        return archive_module_path.exists() and archive_module_path.is_dir()

    def create(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Path:
        """Create new module structure.

        Args:
            name: Module name
            description: Module description
            tags: Module tags

        Returns:
            Path to created module directory

        Raises:
            ModuleError: If creation fails
        """
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        self._validate_module_name(name)

        # Check if module already exists
        module_path = self.modules_path / name
        if module_path.exists():
            raise ModuleError(f"Module already exists: {name}")

        # Create module directory
        try:
            module_path.mkdir(parents=True, exist_ok=False)
        except Exception as e:
            raise ModuleError(f"Failed to create module directory: {e}")

        # Generate module files
        timestamp = datetime.now().strftime("%Y-%m-%d")
        tags_str = ", ".join(tags) if tags else ""

        # module.md
        module_md = f"""# Module: {name}

**Created:** {timestamp}
**Tags:** {tags_str}

## Purpose

{description if description else "TODO: Describe the purpose of this module"}

## Scope

TODO: Define what is included and excluded from this module

## Architecture

TODO: Describe the high-level architecture and design decisions
"""

        # current.md
        current_md = f"""# Current Status

## {timestamp}

### In Progress
- [ ] TODO: Add current tasks

### Completed
- [x] Module created

### Blocked
None

### Next Steps
1. TODO: Define next actions

## Known Issues
None

## Notes
- TODO: Add important notes
"""

        # decisions.md
        decisions_md = f"""# Decisions

## Decision 1: Module Creation ({timestamp})

**Context:** Initial module setup

**Decision:** Created {name} module

**Rationale:** {description if description else "TODO: Document rationale"}

**Consequences:**
- Module structure established
- Ready for development

**Status:** Accepted
"""

        # dependencies.md
        dependencies_md = f"""# Dependencies

## Internal Dependencies

None yet

## External Dependencies

None yet

## Dependents

None yet

## Notes

- TODO: Document dependencies as they are identified
"""

        # interface.md
        interface_md = f"""# Interface

## Public API

TODO: Document public interfaces, commands, or APIs

## Data Structures

TODO: Document key data structures

## Examples

TODO: Add usage examples
"""

        # Write files
        try:
            (module_path / "module.md").write_text(module_md, encoding="utf-8")
            (module_path / "current.md").write_text(current_md, encoding="utf-8")
            (module_path / "decisions.md").write_text(decisions_md, encoding="utf-8")
            (module_path / "dependencies.md").write_text(dependencies_md, encoding="utf-8")
            (module_path / "interface.md").write_text(interface_md, encoding="utf-8")
        except Exception as e:
            # Clean up on failure
            import shutil
            shutil.rmtree(module_path, ignore_errors=True)
            raise ModuleError(f"Failed to create module files: {e}")

        return module_path

    def discover_all_modules(self) -> List[Path]:
        """Discover all modules recursively by finding current.md files.

        Returns:
            List of module paths relative to modules_path
        """
        if not self.modules_path.exists():
            return []

        modules = []
        for current_file in self.modules_path.rglob("current.md"):
            module_dir = current_file.parent

            # Skip archive directories
            if "archive" in module_dir.parts:
                continue

            # Get relative path from modules_path
            try:
                rel_path = module_dir.relative_to(self.modules_path)
                modules.append(rel_path)
            except ValueError:
                continue

        # Sort by path
        modules.sort(key=lambda p: str(p))
        return modules

    def find_module_by_name(self, name: str, exact: bool = False) -> List[str]:
        """Find module(s) by name, searching all module paths.

        Args:
            name: Module name to search for (e.g., 'website' or 'memory-system')
            exact: If True, only exact name matches. If False, matches end of path.

        Returns:
            List of matching module paths (relative to modules_path).
            Empty list if no matches found.

        Examples:
            find_module_by_name('website') -> ['projects/website', 'archive-projects/old-website']
            find_module_by_name('memory-system') -> ['memory-system']
            find_module_by_name('projects/website', exact=True) -> ['projects/website']
        """
        all_modules = self.discover_all_modules()
        matches = []

        for module_path in all_modules:
            module_str = str(module_path)
            module_parts = module_path.parts

            if exact:
                # Exact match: full path must match
                if module_str == name:
                    matches.append(module_str)
            else:
                # Flexible match: name matches last component OR full path
                if module_str == name or module_parts[-1] == name:
                    matches.append(module_str)

        return matches

    def list_modules(self, include_archived: bool = False) -> Dict[str, List[str]]:
        """List all modules (hierarchical paths).

        Args:
            include_archived: Whether to include archived modules

        Returns:
            Dictionary with 'active' (list of paths) and optionally 'archived' lists
        """
        result = {"active": []}

        if not self.modules_path.exists():
            return result

        # List active modules (find all current.md files)
        discovered = self.discover_all_modules()
        result["active"] = [str(p) for p in discovered]

        # List archived modules (flat structure in archive/)
        if include_archived and self.archive_path.exists():
            archived = []
            for item in self.archive_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    archived.append(item.name)
            archived.sort()
            result["archived"] = archived

        return result

    def build_module_tree(self) -> Dict:
        """Build hierarchical tree structure of modules.

        Returns:
            Nested dictionary representing module hierarchy
            Example: {'projects': {'website': {}, 'app': {}}, 'areas': {}}
        """
        modules = self.discover_all_modules()
        tree = {}

        for module_path in modules:
            parts = module_path.parts
            current = tree

            # Build nested structure
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {}
                current = current[part]

        return tree

    def get_module_info(self, name: str) -> Dict:
        """Get information about a module.

        Args:
            name: Module name or path

        Returns:
            Dictionary with module information (path, parent, children)
        """
        module_path = self.modules_path / name

        if not module_path.exists():
            raise ModuleError(f"Module not found: {name}")

        # Check if it's actually a module (has current.md)
        if not (module_path / "current.md").exists():
            raise ModuleError(f"Not a valid module (missing current.md): {name}")

        # Get parent
        rel_path = Path(name)
        parent = str(rel_path.parent) if rel_path.parent != Path(".") else None

        # Get children (direct subdirectories with current.md)
        children = []
        for item in module_path.iterdir():
            if item.is_dir() and (item / "current.md").exists():
                # Skip archive
                if item.name == "archive":
                    continue
                child_path = f"{name}/{item.name}" if name != "." else item.name
                children.append(child_path)

        children.sort()

        return {
            "name": name,
            "path": module_path,
            "parent": parent,
            "children": children,
        }

    def archive(self, name: str, reason: str = "") -> Path:
        """Archive a module.

        Args:
            name: Module name
            reason: Reason for archiving

        Returns:
            Path to archived module

        Raises:
            ModuleError: If archiving fails
        """
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        # Check if module exists
        module_path = self.modules_path / name
        if not module_path.exists():
            raise ModuleError(f"Module not found: {name}")

        # Check if already archived
        if self.is_archived(name):
            raise ModuleError(f"Module already archived: {name}")

        # Create archive directory if needed
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Move module to archive
        import shutil
        archive_module_path = self.archive_path / name

        try:
            shutil.move(str(module_path), str(archive_module_path))
        except Exception as e:
            raise ModuleError(f"Failed to move module to archive: {e}")

        # Update archive index
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        index_path = self.archive_path / "_index.md"

        # Read existing index
        if index_path.exists():
            index_content = index_path.read_text(encoding="utf-8")
        else:
            index_content = "# Archived Modules\n\n"

        # Add new entry
        new_entry = f"""## {name}
- **Archived:** {timestamp}
- **Reason:** {reason if reason else "No reason specified"}
- **Location:** ./{name}/

"""

        index_content += new_entry

        # Write updated index
        try:
            index_path.write_text(index_content, encoding="utf-8")
        except Exception as e:
            raise ModuleError(f"Failed to update archive index: {e}")

        return archive_module_path

    def unarchive(self, name: str) -> Path:
        """Restore module from archive.

        Args:
            name: Module name

        Returns:
            Path to restored module

        Raises:
            ModuleError: If restoration fails
        """
        if not self.archive_path.exists():
            raise ModuleError("Archive directory not found")

        # Check if module is in archive
        archive_module_path = self.archive_path / name
        if not archive_module_path.exists():
            raise ModuleError(f"Module not found in archive: {name}")

        # Check if active module with same name exists
        module_path = self.modules_path / name
        if module_path.exists():
            raise ModuleError(
                f"Active module with name '{name}' already exists. "
                f"Archive or rename it first."
            )

        # Move module from archive to active
        import shutil

        try:
            shutil.move(str(archive_module_path), str(module_path))
        except Exception as e:
            raise ModuleError(f"Failed to restore module from archive: {e}")

        # Update archive index (remove entry)
        index_path = self.archive_path / "_index.md"
        if index_path.exists():
            try:
                content = index_path.read_text(encoding="utf-8")

                # Remove this module's entry (section starting with ## name)
                lines = content.split("\n")
                new_lines = []
                skip_until_next_header = False

                for line in lines:
                    if line.startswith(f"## {name}"):
                        skip_until_next_header = True
                        continue
                    elif line.startswith("## ") and skip_until_next_header:
                        skip_until_next_header = False

                    if not skip_until_next_header:
                        new_lines.append(line)

                # Write updated index
                index_path.write_text("\n".join(new_lines), encoding="utf-8")
            except Exception as e:
                # Non-fatal: module is restored but index not updated
                pass

        return module_path

    def rename(self, old_name: str, new_name: str) -> Path:
        """Rename a module.

        Args:
            old_name: Current module name/path
            new_name: New module name/path

        Returns:
            Path to renamed module

        Raises:
            ModuleError: If renaming fails
        """
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        # Validate new name
        self._validate_module_name(new_name)

        # Check if old module exists
        old_path = self.modules_path / old_name
        if not old_path.exists():
            raise ModuleError(f"Module not found: {old_name}")

        # Check if new module already exists
        new_path = self.modules_path / new_name
        if new_path.exists():
            raise ModuleError(f"Module already exists: {new_name}")

        # Create parent directory for new path if needed
        new_path.parent.mkdir(parents=True, exist_ok=True)

        # Move module
        import shutil
        try:
            shutil.move(str(old_path), str(new_path))
        except Exception as e:
            raise ModuleError(f"Failed to rename module: {e}")

        # Update module.md with new name
        module_md_path = new_path / "module.md"
        if module_md_path.exists():
            try:
                content = module_md_path.read_text(encoding="utf-8")
                # Update the title if it contains the old name
                old_basename = Path(old_name).name
                new_basename = Path(new_name).name
                content = content.replace(
                    f"# Module: {old_basename}",
                    f"# Module: {new_basename}"
                )
                content = content.replace(
                    f"# Module: {old_name}",
                    f"# Module: {new_name}"
                )
                module_md_path.write_text(content, encoding="utf-8")
            except Exception:
                # Non-fatal: module renamed but content not updated
                pass

        return new_path
