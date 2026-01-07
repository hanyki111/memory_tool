"""AST-based Python code parser."""

import ast
from pathlib import Path
from typing import List, Optional, Set

from memory_tool.codemap.models import (
    ClassInfo,
    CodeMap,
    FunctionInfo,
    ModuleInfo,
    Parameter,
)


class PythonParser:
    """Parse Python source files using AST."""

    # Default patterns to exclude
    DEFAULT_EXCLUDE = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        "*.pyc",
        "__init__.py",  # Usually empty or just imports
    }

    # Test file patterns to exclude by default
    TEST_PATTERNS = {
        "test_",
        "_test.py",
        "conftest.py",
        "tests/",
    }

    def __init__(
        self,
        exclude_patterns: Optional[Set[str]] = None,
        include_tests: bool = False,
        include_private: bool = False,
        include_init: bool = False,
    ):
        """Initialize parser.

        Args:
            exclude_patterns: Additional patterns to exclude
            include_tests: Include test files
            include_private: Include private symbols (_name)
            include_init: Include __init__.py files
        """
        self.exclude_patterns = self.DEFAULT_EXCLUDE.copy()
        if exclude_patterns:
            self.exclude_patterns.update(exclude_patterns)
        if include_init:
            self.exclude_patterns.discard("__init__.py")

        self.include_tests = include_tests
        self.include_private = include_private

    def parse_file(self, file_path: Path) -> Optional[ModuleInfo]:
        """Parse a single Python file.

        Args:
            file_path: Path to .py file

        Returns:
            ModuleInfo or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            return None

        module = ModuleInfo(path=file_path)

        # Module docstring
        module.docstring = ast.get_docstring(tree)

        # Parse top-level nodes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._parse_class(node)
                if self._should_include_symbol(class_info):
                    module.classes.append(class_info)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._parse_function(node)
                if self._should_include_symbol(func_info):
                    module.functions.append(func_info)

        return module

    def parse_directory(
        self,
        dir_path: Path,
        relative_to: Optional[Path] = None,
    ) -> CodeMap:
        """Parse all Python files in a directory.

        Args:
            dir_path: Directory to parse
            relative_to: Base path for relative paths in output

        Returns:
            CodeMap containing all parsed modules
        """
        base_path = relative_to or dir_path
        codemap = CodeMap(root_path=base_path)

        if not dir_path.exists():
            return codemap

        # Find all Python files
        py_files = list(dir_path.rglob("*.py"))

        for py_file in sorted(py_files):
            if self._should_exclude_file(py_file):
                continue

            module = self.parse_file(py_file)
            if module and not module.is_empty():
                # Make path relative
                try:
                    module.path = py_file.relative_to(base_path)
                except ValueError:
                    module.path = py_file
                codemap.modules.append(module)

        return codemap

    def _parse_class(self, node: ast.ClassDef) -> ClassInfo:
        """Parse a class definition."""
        class_info = ClassInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            is_private=node.name.startswith("_"),
            bases=[self._get_name(base) for base in node.bases],
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
        )

        # Parse methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._parse_function(item)
                if self._should_include_symbol(method):
                    class_info.methods.append(method)

        return class_info

    def _parse_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> FunctionInfo:
        """Parse a function or method definition."""
        # Check decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        is_classmethod = "classmethod" in decorators
        is_staticmethod = "staticmethod" in decorators
        is_property = "property" in decorators

        func_info = FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=ast.get_docstring(node),
            is_private=node.name.startswith("_") and not node.name.startswith("__"),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_property=is_property,
            decorators=decorators,
            return_annotation=self._get_annotation(node.returns),
        )

        # Parse parameters
        func_info.parameters = self._parse_parameters(node.args)

        return func_info

    def _parse_parameters(self, args: ast.arguments) -> List[Parameter]:
        """Parse function parameters."""
        params = []

        # Calculate defaults offset
        num_args = len(args.args)
        num_defaults = len(args.defaults)
        default_offset = num_args - num_defaults

        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls'
            if arg.arg in ("self", "cls"):
                continue

            default_idx = i - default_offset
            default = None
            if default_idx >= 0 and default_idx < len(args.defaults):
                default = self._get_default_value(args.defaults[default_idx])

            params.append(Parameter(
                name=arg.arg,
                annotation=self._get_annotation(arg.annotation),
                default=default,
            ))

        # *args
        if args.vararg:
            params.append(Parameter(
                name=f"*{args.vararg.arg}",
                annotation=self._get_annotation(args.vararg.annotation),
            ))

        # **kwargs
        if args.kwarg:
            params.append(Parameter(
                name=f"**{args.kwarg.arg}",
                annotation=self._get_annotation(args.kwarg.annotation),
            ))

        return params

    def _get_annotation(self, node: Optional[ast.expr]) -> Optional[str]:
        """Get type annotation as string."""
        if node is None:
            return None
        return self._node_to_string(node)

    def _get_default_value(self, node: ast.expr) -> str:
        """Get default value as string."""
        # Simplify complex defaults
        if isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            if isinstance(node.value, str):
                return f"'{node.value}'" if len(node.value) < 20 else "'...'"
            return str(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, (ast.List, ast.Tuple, ast.Dict)):
            return "..."
        if isinstance(node, ast.Call):
            return f"{self._get_name(node.func)}(...)"
        return "..."

    def _get_name(self, node: ast.expr) -> str:
        """Get name from various node types."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._node_to_string(node.slice)}]"
        return "..."

    def _get_decorator_name(self, node: ast.expr) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._get_name(node.func)
        return "..."

    def _node_to_string(self, node: ast.expr) -> str:
        """Convert AST node to string representation."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._node_to_string(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            value = self._node_to_string(node.value)
            slice_str = self._node_to_string(node.slice)
            return f"{value}[{slice_str}]"
        if isinstance(node, ast.Tuple):
            elements = ", ".join(self._node_to_string(e) for e in node.elts)
            return elements
        if isinstance(node, ast.List):
            elements = ", ".join(self._node_to_string(e) for e in node.elts)
            return f"[{elements}]"
        if isinstance(node, ast.BinOp):
            # Union type: X | Y
            if isinstance(node.op, ast.BitOr):
                left = self._node_to_string(node.left)
                right = self._node_to_string(node.right)
                return f"{left} | {right}"
        if isinstance(node, ast.Call):
            return f"{self._get_name(node.func)}(...)"
        return "..."

    def _should_include_symbol(self, symbol) -> bool:
        """Check if symbol should be included based on settings."""
        if symbol.is_private and not self.include_private:
            # Always include __init__, __str__, etc.
            if symbol.name.startswith("__") and symbol.name.endswith("__"):
                return True
            return False
        return True

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded."""
        path_str = str(file_path)
        name = file_path.name

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in path_str or name == pattern:
                return True

        # Check test patterns
        if not self.include_tests:
            for pattern in self.TEST_PATTERNS:
                if pattern in path_str or name.startswith("test_") or name.endswith("_test.py"):
                    return True

        return False
