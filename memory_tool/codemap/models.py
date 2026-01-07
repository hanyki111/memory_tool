"""Data models for code structure representation."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class SymbolType(Enum):
    """Type of code symbol."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"


@dataclass
class Parameter:
    """Function/method parameter."""

    name: str
    annotation: Optional[str] = None
    default: Optional[str] = None

    def format(self, include_type: bool = True) -> str:
        """Format parameter for display."""
        parts = [self.name]
        if include_type and self.annotation:
            parts.append(f": {self.annotation}")
        if self.default:
            parts.append(f" = {self.default}")
        return "".join(parts)


@dataclass
class CodeSymbol:
    """Base class for code symbols."""

    name: str
    line_number: int
    docstring: Optional[str] = None
    is_private: bool = False

    @property
    def is_public(self) -> bool:
        """Check if symbol is public."""
        return not self.is_private


@dataclass
class FunctionInfo(CodeSymbol):
    """Information about a function or method."""

    parameters: List[Parameter] = field(default_factory=list)
    return_annotation: Optional[str] = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    decorators: List[str] = field(default_factory=list)

    def format_signature(self, include_types: bool = True) -> str:
        """Format function signature."""
        prefix = "async " if self.is_async else ""
        params = ", ".join(p.format(include_types) for p in self.parameters)
        sig = f"{prefix}{self.name}({params})"
        if include_types and self.return_annotation:
            sig += f" -> {self.return_annotation}"
        return sig


@dataclass
class ClassInfo(CodeSymbol):
    """Information about a class."""

    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    class_variables: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)

    def get_public_methods(self) -> List[FunctionInfo]:
        """Get only public methods."""
        return [m for m in self.methods if m.is_public]

    def format_declaration(self) -> str:
        """Format class declaration."""
        if self.bases:
            return f"class {self.name}({', '.join(self.bases)}):"
        return f"class {self.name}:"


@dataclass
class ModuleInfo:
    """Information about a Python module (file)."""

    path: Path
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)

    @property
    def relative_path(self) -> str:
        """Get path as string."""
        return str(self.path)

    def get_public_classes(self) -> List[ClassInfo]:
        """Get only public classes."""
        return [c for c in self.classes if c.is_public]

    def get_public_functions(self) -> List[FunctionInfo]:
        """Get only public functions."""
        return [f for f in self.functions if f.is_public]

    def is_empty(self) -> bool:
        """Check if module has no symbols."""
        return not self.classes and not self.functions


@dataclass
class CodeMap:
    """Complete code map for a project or directory."""

    root_path: Path
    modules: List[ModuleInfo] = field(default_factory=list)

    @property
    def total_classes(self) -> int:
        """Total number of classes."""
        return sum(len(m.classes) for m in self.modules)

    @property
    def total_functions(self) -> int:
        """Total number of top-level functions."""
        return sum(len(m.functions) for m in self.modules)

    @property
    def total_methods(self) -> int:
        """Total number of methods."""
        return sum(
            len(c.methods)
            for m in self.modules
            for c in m.classes
        )

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the code map."""
        return {
            "modules": len(self.modules),
            "classes": self.total_classes,
            "functions": self.total_functions,
            "methods": self.total_methods,
        }
