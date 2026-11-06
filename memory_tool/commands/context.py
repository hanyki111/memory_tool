"""Context-related CLI commands (context, map)."""

import sys
from pathlib import Path
from typing import Optional

import typer

from memory_tool.commands.common import app, console
from memory_tool.context.builder import ContextBuilder, ContextError
from memory_tool.utils.path_checker import PathChecker
from memory_tool.utils.paths import display_path, get_base_path


@app.command()
def context(
    output: str = typer.Option(None, "--output", "-o", help="Output file path (default: .claude/memory-context.md)"),
    structure: bool = typer.Option(False, "--structure", "-s", help="Include module-source mapping in context"),
    with_map: bool = typer.Option(False, "--with-map", "-m", help="Generate code-context.md with Python code structure"),
    map_depth: str = typer.Option("structure", "--map-depth", help="Code map depth: overview, structure (default), api, docs"),
    map_path: str = typer.Option(None, "--map-path", help="Path to analyze for code map (default: current directory)"),
    check_health_only: bool = typer.Option(False, "--check-health-only", help="Only check document health and exit (for git hooks)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Quiet mode (minimal output)"),
):
    """Build context for Claude Code (mcontext command).

    With --with-map, also generates code-context.md containing Python code
    structure (classes, methods, signatures) for AI-assisted development.
    """
    if check_health_only:
        from memory_tool.utils.health_checker import DocumentHealthChecker

        memory_dir = get_base_path()
        checker = DocumentHealthChecker(memory_dir)

        critical_issues = checker.get_critical_issues()
        warning_issues = checker.get_warning_issues()

        if critical_issues:
            if not quiet:
                console.print("\n[red]CRITICAL[/red] Document Health Issues:\n")
                for issue in critical_issues[:5]:
                    console.print(f"  - {issue.module_name}/{issue.file_type}.md: [yellow]{issue.line_count}[/yellow] lines")
                console.print()
                console.print("  [dim]Recommend archiving before commit:[/dim]")
                console.print(f"  [cyan]marchive decisions --suggest[/cyan]")
            sys.exit(2)
        elif warning_issues:
            if not quiet:
                console.print("\n[yellow]WARNING[/yellow] Document Health Issues:\n")
                for issue in warning_issues[:5]:
                    console.print(f"  - {issue.module_name}/{issue.file_type}.md: [yellow]{issue.line_count}[/yellow] lines")
                console.print()
                console.print("  [dim]Consider archiving:[/dim]")
                console.print(f"  [cyan]marchive decisions --suggest[/cyan]")
            sys.exit(1)
        else:
            if not quiet:
                console.print("[green]OK[/green] Document health OK")
            sys.exit(0)

    builder = ContextBuilder()
    output_path = Path(output) if output else None

    try:
        result_path = builder.write_context(output_path, include_structure=structure)

        if not quiet:
            try:
                rel_path = display_path(result_path)
            except ValueError:
                rel_path = result_path
            console.print(f"[green]OK[/green] Context built successfully")
            console.print(f"[dim]-> {rel_path}[/dim]")

            config = builder.load_config()
            recent_days = config.get("context", {}).get("recent_days", 3)
            timeline_count = len(builder.get_recent_timeline_paths(recent_days))
            module_count = len(builder.get_module_statuses())

            console.print(f"[dim]Included: {timeline_count} timeline(s), {module_count} module(s)[/dim]")

            if structure:
                console.print(f"[dim]Module-source mapping: included[/dim]")

            path_checker = PathChecker()
            cached_warning = path_checker.get_cached_summary()
            if cached_warning:
                console.print(f"[yellow]Path issues:[/yellow] {cached_warning}")
                console.print(f"[dim]Run 'mcheck' for details[/dim]")

        if with_map:
            from memory_tool.codemap import PythonParser, CodeMapFormatter, DepthLevel

            valid_depths = ["overview", "structure", "api", "docs"]
            if map_depth not in valid_depths:
                console.print(f"[yellow]![/yellow] Invalid map depth: {map_depth}, using 'structure'")
                map_depth = "structure"

            analysis_path = Path(map_path) if map_path else Path.cwd()
            if not analysis_path.exists():
                console.print(f"[yellow]![/yellow] Map path not found: {map_path}")
            else:
                py_files = list(analysis_path.rglob("*.py")) if analysis_path.is_dir() else []
                if analysis_path.is_dir() and not py_files:
                    console.print(f"[yellow]![/yellow] No Python files found for code map")
                else:
                    parser = PythonParser()
                    if analysis_path.is_dir():
                        codemap = parser.parse_directory(analysis_path, relative_to=Path.cwd())
                    else:
                        module_obj = parser.parse_file(analysis_path)
                        from memory_tool.codemap.models import CodeMap
                        codemap = CodeMap(root_path=Path.cwd(), modules=[module_obj] if module_obj else [])

                    if codemap.modules:
                        formatter = CodeMapFormatter(depth=DepthLevel(map_depth))
                        map_content = formatter.format(codemap)

                        claude_dir = Path.cwd() / ".claude"
                        claude_dir.mkdir(exist_ok=True)
                        code_context_path = claude_dir / "code-context.md"

                        header = f"# Code Structure Map\n\nGenerated by `mcontext --with-map`\nDepth: {map_depth}\n\n"
                        code_context_path.write_text(header + map_content, encoding="utf-8")

                        if not quiet:
                            stats = codemap.get_stats()
                            console.print(f"[green]OK[/green] Code map generated")
                            console.print(f"[dim]-> .claude/code-context.md ({stats['classes']} classes, {stats['methods']} methods)[/dim]")

    except ContextError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command(name="map")
def code_map(
    path: str = typer.Argument(".", help="Path to analyze (file or directory)"),
    depth: str = typer.Option("structure", "--depth", "-d", help="Output depth: overview, structure (default), api, docs"),
    private: bool = typer.Option(False, "--private", "-p", help="Include private symbols (_name)"),
    tests: bool = typer.Option(False, "--tests", "-t", help="Include test files"),
    output: str = typer.Option(None, "--output", "-o", help="Write output to file instead of stdout"),
):
    """Generate code map from Python source files (mmap command).

    Analyzes Python source code using AST and outputs structure information.

    Depth levels:
    - overview:  Class names with docstrings
    - structure: + Method names (default)
    - api:       + Full type signatures
    - docs:      + Method docstrings

    Examples:
        mmap                           # Current directory, structure depth
        mmap src/                      # Specific directory
        mmap --depth=api               # Full signatures
        mmap --private                 # Include private symbols
        mmap -o code-map.md            # Write to file
    """
    from memory_tool.codemap import PythonParser, CodeMapFormatter, DepthLevel

    try:
        target_path = Path(path).resolve()

        if not target_path.exists():
            console.print(f"[red]ERROR[/red] Path not found: {path}")
            sys.exit(1)

        valid_depths = ["overview", "structure", "api", "docs"]
        if depth not in valid_depths:
            console.print(f"[red]ERROR[/red] Invalid depth: {depth}")
            console.print(f"[dim]Valid depths: {', '.join(valid_depths)}[/dim]")
            sys.exit(1)

        if target_path.is_file():
            if not target_path.suffix == ".py":
                console.print(f"[yellow]![/yellow] Not a Python file: {path}")
                console.print("[dim]mmap currently supports Python only.[/dim]")
                sys.exit(1)
        else:
            py_files = list(target_path.rglob("*.py"))
            if not py_files:
                all_files = list(target_path.rglob("*"))
                extensions = set(
                    f.suffix for f in all_files
                    if f.is_file() and f.suffix
                    and len(f.suffix) <= 10
                    and f.suffix[1:].replace("_", "").isalnum()
                )
                console.print(f"[yellow]![/yellow] No Python files found in: {path}")
                if extensions:
                    console.print(f"[dim]Found file types: {', '.join(sorted(extensions))}[/dim]")
                console.print("[dim]mmap currently supports Python only.[/dim]")
                console.print("[dim]Alternatives: Use 'ctags' for multi-language support[/dim]")
                sys.exit(1)

        parser = PythonParser(include_tests=tests, include_private=private)
        base_path = Path.cwd()

        if target_path.is_file():
            module_obj = parser.parse_file(target_path)
            if module_obj:
                try:
                    module_obj.path = target_path.relative_to(base_path)
                except ValueError:
                    module_obj.path = target_path

                from memory_tool.codemap.models import CodeMap
                codemap = CodeMap(root_path=base_path, modules=[module_obj])
            else:
                console.print(f"[red]ERROR[/red] Failed to parse: {path}")
                sys.exit(1)
        else:
            codemap = parser.parse_directory(target_path, relative_to=base_path)

        if not codemap.modules:
            console.print("[yellow]![/yellow] No public symbols found.")
            sys.exit(0)

        formatter = CodeMapFormatter(depth=DepthLevel(depth), include_private=private)
        result = formatter.format(codemap)

        if output:
            output_path = Path(output)
            output_path.write_text(result, encoding="utf-8")
            console.print(f"[green]OK[/green] Code map written to: {output}")
        else:
            console.print(result)

    except Exception as e:
        console.print(f"[red]ERROR[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
