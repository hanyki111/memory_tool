"""Output formatters for code maps."""

from enum import Enum
from pathlib import Path
from typing import List, Optional

from memory_tool.codemap.models import (
    ClassInfo,
    CodeMap,
    FunctionInfo,
    ModuleInfo,
)


class DepthLevel(Enum):
    """Output depth levels."""

    OVERVIEW = "overview"      # L2: class + docstring
    STRUCTURE = "structure"    # L3: + method names (default)
    API = "api"               # L5: + full signatures
    DOCS = "docs"             # L6: + method docstrings


class CodeMapFormatter:
    """Format code maps for display."""

    def __init__(
        self,
        depth: DepthLevel = DepthLevel.STRUCTURE,
        include_private: bool = False,
        indent: str = "  ",
    ):
        """Initialize formatter.

        Args:
            depth: Output depth level
            include_private: Include private symbols
            indent: Indentation string
        """
        self.depth = depth
        self.include_private = include_private
        self.indent = indent

    def format(self, codemap: CodeMap) -> str:
        """Format entire code map."""
        if not codemap.modules:
            return "No Python modules found."

        lines = []
        for module in codemap.modules:
            module_output = self.format_module(module)
            if module_output:
                lines.append(module_output)

        if not lines:
            return "No public symbols found."

        # Add summary
        stats = codemap.get_stats()
        lines.append("")
        lines.append(f"# {stats['modules']} modules, {stats['classes']} classes, "
                     f"{stats['functions']} functions, {stats['methods']} methods")

        return "\n".join(lines)

    def format_module(self, module: ModuleInfo) -> str:
        """Format a single module."""
        lines = []
        path_str = str(module.path).replace("\\", "/")
        lines.append(path_str)

        # Classes
        classes = module.classes if self.include_private else module.get_public_classes()
        for cls in classes:
            class_output = self.format_class(cls, level=1)
            if class_output:
                lines.append(class_output)

        # Top-level functions
        functions = module.functions if self.include_private else module.get_public_functions()
        for func in functions:
            func_output = self.format_function(func, level=1)
            if func_output:
                lines.append(func_output)

        # Only return if we have content beyond the path
        if len(lines) > 1:
            return "\n".join(lines)
        return ""

    def format_class(self, cls: ClassInfo, level: int = 0) -> str:
        """Format a class definition."""
        lines = []
        indent = self.indent * level

        # Class declaration
        if self.depth == DepthLevel.OVERVIEW:
            # L2: class name + docstring
            header = f"{indent}class {cls.name}"
            if cls.bases:
                header += f"({', '.join(cls.bases)})"
            lines.append(header)
            if cls.docstring:
                first_line = cls.docstring.split("\n")[0].strip()
                if first_line:
                    lines.append(f"{indent}{self.indent}# {first_line}")
        else:
            # L3+: class declaration
            lines.append(f"{indent}{cls.format_declaration()}")

            # Add docstring for DOCS level
            if self.depth == DepthLevel.DOCS and cls.docstring:
                first_line = cls.docstring.split("\n")[0].strip()
                if first_line:
                    lines.append(f"{indent}{self.indent}\"\"\"{first_line}\"\"\"")

            # Methods
            methods = cls.methods if self.include_private else cls.get_public_methods()
            for method in methods:
                method_output = self.format_function(method, level=level + 1)
                if method_output:
                    lines.append(method_output)

        return "\n".join(lines)

    def format_function(self, func: FunctionInfo, level: int = 0) -> str:
        """Format a function or method."""
        indent = self.indent * level

        if self.depth == DepthLevel.OVERVIEW:
            # L2: Not shown for methods in overview
            return ""

        if self.depth == DepthLevel.STRUCTURE:
            # L3: Just name
            prefix = ""
            if func.is_property:
                prefix = "@property "
            elif func.is_classmethod:
                prefix = "@classmethod "
            elif func.is_staticmethod:
                prefix = "@staticmethod "
            return f"{indent}{prefix}{func.name}"

        # L5/L6: Full signature
        sig = func.format_signature(include_types=True)

        # Add decorators indicator
        prefix = ""
        if func.is_property:
            prefix = "@property "
        elif func.is_classmethod:
            prefix = "@classmethod "
        elif func.is_staticmethod:
            prefix = "@staticmethod "

        line = f"{indent}{prefix}{sig}"

        # L6: Add docstring
        if self.depth == DepthLevel.DOCS and func.docstring:
            first_line = func.docstring.split("\n")[0].strip()
            if first_line:
                line += f"\n{indent}{self.indent}# {first_line}"

        return line

    def format_for_interface(self, codemap: CodeMap) -> str:
        """Format code map for interface.md (always API level)."""
        old_depth = self.depth
        self.depth = DepthLevel.API

        lines = ["<!-- AUTO-GENERATED BY mmap - DO NOT EDIT -->", ""]

        for module in codemap.modules:
            module_output = self._format_module_for_interface(module)
            if module_output:
                lines.append(module_output)
                lines.append("")

        self.depth = old_depth
        return "\n".join(lines)

    def _format_module_for_interface(self, module: ModuleInfo) -> str:
        """Format module for interface.md."""
        lines = []
        path_str = str(module.path).replace("\\", "/")
        lines.append(f"## {path_str}")
        lines.append("")

        # Public classes
        for cls in module.get_public_classes():
            lines.append(f"### {cls.format_declaration()}")
            if cls.docstring:
                first_line = cls.docstring.split("\n")[0].strip()
                if first_line:
                    lines.append(f"> {first_line}")
            lines.append("")
            lines.append("```python")
            for method in cls.get_public_methods():
                sig = method.format_signature(include_types=True)
                lines.append(f"{sig}")
            lines.append("```")
            lines.append("")

        # Public functions
        public_funcs = module.get_public_functions()
        if public_funcs:
            lines.append("### Functions")
            lines.append("")
            lines.append("```python")
            for func in public_funcs:
                sig = func.format_signature(include_types=True)
                lines.append(sig)
            lines.append("```")

        return "\n".join(lines) if len(lines) > 2 else ""


def format_codemap(
    codemap: CodeMap,
    depth: str = "structure",
    include_private: bool = False,
) -> str:
    """Convenience function to format a code map.

    Args:
        codemap: CodeMap to format
        depth: Depth level name (overview, structure, api, docs)
        include_private: Include private symbols

    Returns:
        Formatted string
    """
    depth_level = DepthLevel(depth)
    formatter = CodeMapFormatter(depth=depth_level, include_private=include_private)
    return formatter.format(codemap)
