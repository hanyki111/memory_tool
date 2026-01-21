"""Common utilities and shared resources for CLI commands."""

from typing import Optional

import typer
from rich.console import Console

from memory_tool.core.module import ModuleManager

# Shared app instance
app = typer.Typer(
    name="memory-tool",
    help="Time-Space Integrated Knowledge System",
    add_completion=False,
)

# Shared console instance
console = Console()


def sanitize_output(text: str) -> str:
    """Remove characters that cause issues with Windows console.

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    replacements = {
        '⭐': '*',
        '✅': '[OK]',
        '❌': '[X]',
        '⚠️': '[!]',
        '⚠': '[!]',
        '🎯': '[TARGET]',
        '🔄': '[REFRESH]',
        '📝': '[NOTE]',
        '💡': '[IDEA]',
        '🚀': '[LAUNCH]',
        '✨': '[NEW]',
        '🔍': '[SEARCH]',
        '📌': '[PIN]',
        '🎉': '[DONE]',
        '💪': '[STRONG]',
        '🤔': '[THINK]',
        '📋': '[LIST]',
        '🔗': '[LINK]',
    }

    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)

    return text


def opt_str(value) -> Optional[str]:
    """Safely convert Typer option value to str or None.

    Typer 0.12.0+ may return OptionInfo objects instead of None
    when optional parameters are not provided. This function handles that.

    Args:
        value: Value from typer.Option (could be str, None, or OptionInfo)

    Returns:
        str if value is a string, None otherwise
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return None


def arg_str(value) -> str:
    """Safely convert Typer argument value to str.

    Typer 0.12.0+ may return ArgumentInfo objects instead of actual values
    in some edge cases. This function handles that.

    Args:
        value: Value from typer.Argument (could be str or ArgumentInfo)

    Returns:
        str value

    Raises:
        typer.BadParameter: If value is not a valid string
    """
    if isinstance(value, str):
        return value
    raise typer.BadParameter(f"Invalid argument value: {type(value).__name__}")


def resolve_module_name(module_name: str) -> str:
    """Resolve module name to full path by searching all modules.

    Args:
        module_name: Module name or path (e.g., 'website' or 'projects/website')

    Returns:
        Full module path (e.g., 'projects/website')

    Raises:
        typer.Exit: If module not found or multiple matches require selection
    """
    if not module_name:
        return None

    manager = ModuleManager()
    matches = manager.find_module_by_name(module_name, exact=True)

    if len(matches) == 1:
        return matches[0]

    if len(matches) == 0:
        matches = manager.find_module_by_name(module_name, exact=False)

    if len(matches) == 0:
        console.print(f"[red]ERROR[/red] Module not found: {module_name}")
        console.print("[dim]Use 'python -m memory_tool module list' to see all modules[/dim]")
        raise typer.Exit(1)
    elif len(matches) == 1:
        resolved = matches[0]
        if resolved != module_name:
            console.print(f"[dim]Resolved '{module_name}' -> '{resolved}'[/dim]")
        return resolved
    else:
        console.print(f"[yellow]Multiple modules match '{module_name}':[/yellow]")
        for i, match in enumerate(matches, 1):
            console.print(f"  {i}. {match}")
        console.print("\n[dim]Please specify the full path (e.g., --module projects/website)[/dim]")
        raise typer.Exit(1)
