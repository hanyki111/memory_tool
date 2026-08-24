"""Module management functionality."""

import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from memory_tool.utils.paths import base_dir_for_root, get_project_root


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
            base_path = get_project_root()
        self.base_path = Path(base_path)
        self.memory_path = base_dir_for_root(self.base_path)
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
        """Get file path for a module following [Folder]/[Folder].md convention."""
        mod_basename = Path(name).name
        return self.modules_path / name / f"{mod_basename}.md"

    def module_exists(self, name: str) -> bool:
        """Check if module exists (as single file in folder or old format)."""
        file_path = self.get_module_file_path(name)
        if file_path.exists() and file_path.is_file():
            return True
        # Check flat single file format (e.g., .memory/modules/name.md)
        flat_file = self.modules_path / f"{name}.md"
        if flat_file.exists() and flat_file.is_file():
            return True
        # Check legacy directory format
        dir_path = self.modules_path / name
        return dir_path.exists() and dir_path.is_dir() and ((dir_path / "module.md").exists() or (dir_path / "current.md").exists())

    #: Filenames used by the legacy multi-file module layout, in the order they
    #: should be preferred when looking for a module's main document.
    LEGACY_DOC_NAMES = ("current.md", "module.md")

    def resolve_module_doc(self, name: str) -> Optional[Path]:
        """Find a module's primary markdown document.

        Three layouts exist and all are still readable:
          1. ``<name>/<basename>.md``  -- current single-file encapsulation
          2. ``<name>.md``             -- flat single file
          3. ``<name>/current.md``     -- legacy multi-file

        Callers that only checked for ``current.md`` silently skipped every
        module in the first two layouts.

        Args:
            name: Module name or relative path

        Returns:
            Path to the module's main document, or None if none exists.
        """
        encapsulated = self.get_module_file_path(name)
        if encapsulated.is_file():
            return encapsulated

        flat = self.modules_path / f"{name}.md"
        if flat.is_file():
            return flat

        module_dir = self.modules_path / name
        for legacy_name in self.LEGACY_DOC_NAMES:
            legacy = module_dir / legacy_name
            if legacy.is_file():
                return legacy

        return None

    def is_archived(self, name: str) -> bool:
        """Check if module is archived."""
        if not self.archive_path.exists():
            return False

        mod_basename = Path(name).name
        archive_encapsulated = self.archive_path / name / f"{mod_basename}.md"
        archive_flat = self.archive_path / f"{name}.md"
        archive_dir = self.archive_path / name
        return archive_encapsulated.exists() or archive_flat.exists() or (archive_dir.exists() and archive_dir.is_dir())

    def create(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        kind: Optional[str] = None,
        nature: Optional[str] = None,
        draft: bool = False,
    ) -> Path:
        """Create new single-file module structure at [Folder]/[Folder].md.

        Args:
            name: Module name or path (e.g. 'memory-tool' or 'memory-tool/core-system')
            description: Module description
            tags: Module tags
            kind: Template kind -- "knowledge", "implementation" or "intent".
                When omitted, the value of ``modules.default_kind`` in config is
                used; if that is unset too, the original generic template is
                produced.
            nature: Body outline. knowledge takes concept, reference, analysis,
                tracker or method; intent takes idea, inquiry or plan.
            draft: Write the seed document instead of the full skeleton. Grow it
                later with ``grow()``. Requires a kind, since the seed is
                kind-specific.

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

        resolved_kind = self._resolve_kind(kind, nature)

        if draft and resolved_kind is None:
            raise ModuleError(
                "--draft needs a kind, because the seed document differs per "
                "kind. Pass --kind knowledge|implementation|intent, or set "
                "modules.default_kind."
            )

        if resolved_kind is not None:
            return self._create_from_template(
                file_path=file_path,
                name=name,
                kind=resolved_kind,
                nature=nature,
                description=description,
                tags=tags,
                draft=draft,
            )

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

    def _resolve_kind(self, kind: Optional[str], nature: Optional[str]) -> Optional[str]:
        """Decide which template kind to use.

        Explicit ``kind`` wins. Otherwise ``modules.default_kind`` from config
        applies, which lets a knowledge-oriented project opt in once instead of
        passing --kind on every create. A bare ``nature`` names its own kind,
        since no nature name is shared between kinds.

        Returns:
            The kind name, or None to use the original generic template.
        """
        if kind:
            return kind
        if nature:
            from memory_tool.core.module_templates import (
                NATURE_KIND,
                kind_for_nature,
            )

            # An unknown name still resolves to a kind so that the template
            # layer reports it, rather than silently producing a bare module.
            return kind_for_nature(nature) or NATURE_KIND

        try:
            from memory_tool.utils.config import Config

            configured = Config(self.memory_path).get("modules.default_kind")
        except Exception:
            return None

        return configured or None

    #: The classification line a templated module carries, e.g.
    #: "**Kind:** intent | **Nature:** plan | **Stage:** 착상 | ..."
    _KIND_LINE = re.compile(r"^\*\*Kind:\*\*.*$", re.MULTILINE)
    _KIND_VALUE = re.compile(r"\*\*Kind:\*\*\s*([a-z]+)")
    _NATURE_VALUE = re.compile(r"\*\*Nature:\*\*\s*([a-z]+)\s*(?:\||$)")

    def read_classification(self, name: str) -> Dict[str, Optional[str]]:
        """Read a module's Kind and Nature from its own header.

        Growing a draft needs the same classification the draft was created
        with; asking for it again would invite a different answer, and a module
        whose header says one thing and whose body outline says another is worse
        than either.

        Args:
            name: Module name or path

        Returns:
            {"kind": str or None, "nature": str or None}. Both are None for a
            module made from the generic template, which carries no Kind line.
        """
        doc = self.resolve_module_doc(name)
        if doc is None:
            raise ModuleError(f"Module not found: {name}")

        text = doc.read_text(encoding="utf-8")
        line_match = self._KIND_LINE.search(text)
        if line_match is None:
            return {"kind": None, "nature": None}

        line = line_match.group(0)
        kind = self._KIND_VALUE.search(line)
        nature = self._NATURE_VALUE.search(line)

        return {
            "kind": kind.group(1) if kind else None,
            "nature": nature.group(1) if nature else None,
        }

    def grow(
        self,
        name: str,
        kind: Optional[str] = None,
        nature: Optional[str] = None,
    ) -> tuple:
        """Append the skeleton sections a module does not have yet.

        The second half of the draft workflow: a seed grows into the full
        document without the author copying sections out of the template. What
        is already written is left exactly as it is.

        Args:
            name: Module name or path
            kind: Override the kind in the module's header
            nature: Override the nature in the module's header

        Returns:
            (path, list of part names appended). The list is empty when the
            module already has every section.

        Raises:
            ModuleError: If the module is missing, carries no kind, or the
                templates cannot be loaded.
        """
        from memory_tool.core.module_templates import (
            TemplateError,
            grow_module_document,
        )

        doc = self.resolve_module_doc(name)
        if doc is None:
            raise ModuleError(f"Module not found: {name}")

        found = self.read_classification(name)
        resolved_kind = kind or found["kind"]
        resolved_nature = nature or found["nature"]

        if resolved_kind is None:
            raise ModuleError(
                f"'{name}' has no '**Kind:**' line, so there is no skeleton to "
                f"grow into. Pass --kind knowledge|implementation|intent."
            )

        existing = doc.read_text(encoding="utf-8")

        try:
            grown, added = grow_module_document(
                existing,
                name=name,
                kind=resolved_kind,
                nature=resolved_nature,
                memory_path=self.memory_path,
            )
        except TemplateError as e:
            raise ModuleError(str(e)) from e

        if added:
            try:
                doc.write_text(grown, encoding="utf-8")
            except Exception as e:
                raise ModuleError(f"Failed to write module file: {e}")

        return doc, added

    def _create_from_template(
        self,
        file_path: Path,
        name: str,
        kind: str,
        nature: Optional[str],
        description: str,
        tags: Optional[List[str]],
        draft: bool = False,
    ) -> Path:
        """Write a module assembled from the MOP templates."""
        from memory_tool.core.module_templates import (
            TemplateError,
            build_module_document,
        )

        try:
            content = build_module_document(
                name=name,
                kind=kind,
                nature=nature,
                description=description,
                tags=tags,
                memory_path=self.memory_path,
                draft=draft,
            )
        except TemplateError as e:
            raise ModuleError(str(e)) from e

        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise ModuleError(f"Failed to create module file: {e}")

        return file_path

    def discover_all_modules(self) -> List[Path]:
        """Discover all modules recursively by finding module markdown files.

        Returns:
            List of module relative paths (without .md extension) sorted by path.
        """
        if not self.modules_path.exists():
            return []

        modules = set()

        for md_file in self.modules_path.rglob("*.md"):
            # Skip archive directory
            if "archive" in md_file.parts:
                continue
            # Skip uppercase meta summary files or index files starting with _ or special files
            if md_file.name.startswith("_") or md_file.name.isupper() or md_file.name in ["MIGRATION-SUMMARY.md"]:
                continue

            # Case 1: Legacy multi-file module (module.md, current.md, etc.)
            if md_file.name in ["module.md", "current.md", "decisions.md", "dependencies.md", "interface.md"]:
                legacy_dir = md_file.parent
                try:
                    rel_legacy = legacy_dir.relative_to(self.modules_path)
                    modules.add(rel_legacy)
                except ValueError:
                    pass
                continue

            # Case 2: [Folder]/[Folder].md (e.g. memory-tool/core-system/core-system.md)
            if md_file.stem == md_file.parent.name:
                try:
                    rel_path = md_file.parent.relative_to(self.modules_path)
                    modules.add(rel_path)
                    continue
                except ValueError:
                    pass

            # Case 3: Flat single-file module (e.g. memory-tool/core-system.md)
            try:
                rel_path = md_file.relative_to(self.modules_path).with_suffix("")
                modules.add(rel_path)
            except ValueError:
                continue

        result = list(modules)
        result.sort(key=lambda p: str(p))
        return result

    def find_module_by_name(self, name: str, exact: bool = False) -> List[str]:
        """Find module(s) by name, searching all module paths.

        Comparison is on the forward-slash form. Everything else in the system
        writes module paths that way -- ``mmodule create "a/b"``, ``[[a/b]]``
        wiki links, the docs -- but discovery yields ``Path`` objects, whose
        ``str()`` uses a backslash on Windows. A nested module therefore never
        matched the name its own creation command was given.
        """
        wanted = Path(name).as_posix()
        matches = []

        for module_path in self.discover_all_modules():
            module_str = module_path.as_posix()

            if exact:
                if module_str == wanted:
                    matches.append(module_str)
            else:
                if module_str == wanted or module_path.parts[-1] == wanted:
                    matches.append(module_str)

        return matches

    def list_modules(self, include_archived: bool = False) -> Dict[str, List[str]]:
        """List all modules."""
        result = {"active": []}

        if not self.modules_path.exists():
            return result

        # Forward slashes, matching what users type and what wiki links use.
        discovered = self.discover_all_modules()
        result["active"] = [p.as_posix() for p in discovered]

        if include_archived and self.archive_path.exists():
            archived = []
            for item in self.archive_path.rglob("*.md"):
                if "archive" in item.parts and not item.name.startswith("_") and not item.name.isupper():
                    if item.stem == item.parent.name:
                        rel = item.parent.relative_to(self.archive_path)
                        archived.append(str(rel))
                    else:
                        rel = item.relative_to(self.archive_path).with_suffix("")
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
        flat_file = self.modules_path / f"{name}.md"
        legacy_dir = self.modules_path / name

        exists = file_path.exists() or flat_file.exists() or (legacy_dir.exists() and legacy_dir.is_dir())
        if not exists:
            raise ModuleError(f"Module not found: {name}")

        rel_path = Path(name)
        parent = str(rel_path.parent) if rel_path.parent != Path(".") else None

        all_modules = self.discover_all_modules()
        children = []
        for mod in all_modules:
            mod_str = str(mod)
            if mod_str != name and mod_str.startswith(f"{name}/"):
                sub = mod_str[len(name) + 1:]
                if "/" not in sub:
                    children.append(mod_str)

        children.sort()

        actual_path = file_path if file_path.exists() else (flat_file if flat_file.exists() else legacy_dir)

        return {
            "name": name,
            "path": actual_path,
            "parent": parent,
            "children": children,
        }

    def migrate_module(self, name_or_path: str) -> Path:
        """Migrate legacy multi-file or flat module into [Folder]/[Folder].md directory encapsulated structure.

        Args:
            name_or_path: Module relative path (e.g. 'memory-tool/core-system')

        Returns:
            Path to newly created single module markdown file (.md) inside its own folder.
        """
        target_file = self.get_module_file_path(name_or_path)
        flat_file = self.modules_path / f"{name_or_path}.md"
        dir_path = self.modules_path / name_or_path

        # Case A: Module is flat file (e.g., .memory/modules/memory-tool/core-system.md)
        if flat_file.exists() and flat_file.is_file() and flat_file != target_file:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(flat_file), str(target_file))
            return target_file

        # Case B: Already in target format
        if target_file.exists() and target_file.is_file():
            return target_file

        # Case C: Legacy directory with multiple files
        if not dir_path.exists() or not dir_path.is_dir():
            raise ModuleError(f"Legacy module directory not found: {name_or_path}")

        std_files = ["module.md", "current.md", "decisions.md", "dependencies.md", "interface.md"]
        combined_sections = []

        module_md_path = dir_path / "module.md"
        if module_md_path.exists():
            combined_sections.append(module_md_path.read_text(encoding="utf-8").strip())
        else:
            combined_sections.append(f"# Module: {Path(name_or_path).name}\n")

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
                if not content.startswith("#"):
                    content = f"{default_title}\n\n{content}"
                combined_sections.append(content)

        for extra_file in dir_path.iterdir():
            if extra_file.is_file() and extra_file.suffix == ".md" and extra_file.name not in std_files and extra_file.name != target_file.name:
                content = extra_file.read_text(encoding="utf-8").strip()
                combined_sections.append(f"## {extra_file.stem.capitalize()}\n\n{content}")

        combined_content = "\n\n---\n\n".join(combined_sections) + "\n"

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(combined_content, encoding="utf-8")

        for fname in std_files:
            fpath = dir_path / fname
            if fpath.exists():
                fpath.unlink()

        return target_file

    def migrate_all_modules(self) -> List[Path]:
        """Find and migrate all legacy multi-file or flat module files into [Folder]/[Folder].md format.

        Returns:
            List of created/migrated single module .md file paths.
        """
        migrated = []
        if not self.modules_path.exists():
            return migrated

        # 1. First discover all existing module names
        all_modules = self.discover_all_modules()

        # Sort deeper modules first so submodules migrate before parents
        all_modules.sort(key=lambda p: len(p.parts), reverse=True)

        for mod_path in all_modules:
            mod_str = str(mod_path).replace("\\", "/")
            try:
                res = self.migrate_module(mod_str)
                migrated.append(res)
            except Exception as e:
                print(f"Warning: Failed to migrate module '{mod_str}': {e}")

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

