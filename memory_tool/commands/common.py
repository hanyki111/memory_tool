"""Common utilities and shared resources for CLI commands."""

from typing import Optional, Callable
import sys
import click

import typer
from rich.console import Console

from memory_tool.core.module import ModuleManager


def get_help_language() -> str:
    """Get help language from config."""
    try:
        from memory_tool.utils.config import Config
        cfg = Config()
        return cfg.get("help.language", "en")
    except Exception:
        return "en"


def get_bilingual_help(en: str, ko: str) -> str:
    """Get help text in the configured language.

    Args:
        en: English help text
        ko: Korean help text

    Returns:
        Help text in configured language
    """
    lang = get_help_language()
    return ko if lang == "ko" else en


def show_bilingual_help(ctx: click.Context, command_name: str) -> None:
    """Show bilingual help for a command and exit."""
    from memory_tool.commands.help import HELP_CONTENT

    lang = get_help_language()
    console = Console()

    # Normalize command name
    cmd_map = {
        "m": "record", "기": "record",
        "ms": "search", "검": "search",
        "mask": "ask", "질문": "ask",
        "mtoday": "today", "오늘": "today",
        "mweek": "week", "주간": "week",
        "mmonth": "month", "월간": "month",
        "mdays": "days", "일수": "days",
        "msort": "sort",
        "mbrowse": "browse",
        "mcheck": "check",
        "mmodule": "module",
        "marchive": "archive",
        "mcontext": "context",
        "mmap": "map",
        "mplan": "plan",
        "msummary": "summary",
        "mproviders": "providers",
        "minit": "init",
        "mstatus": "status",
        "mtutorial": "tutorial",
        "malias": "alias",
        "mconfig": "config",
        "mhooks": "hooks",
        "mcompletion": "completion",
    }
    cmd = cmd_map.get(command_name, command_name)

    if cmd in HELP_CONTENT:
        help_data = HELP_CONTENT[cmd].get(lang, HELP_CONTENT[cmd].get("en", {}))

        if help_data:
            # Header
            console.print(f"\n[bold cyan]{help_data.get('name', cmd)}[/bold cyan]")
            console.print(f"[dim]{help_data.get('summary', '')}[/dim]\n")

            # Description
            if lang == "ko":
                console.print("[bold]설명:[/bold]")
            else:
                console.print("[bold]Description:[/bold]")
            console.print(help_data.get('description', '').strip())
            console.print("")

            # Examples
            examples = help_data.get('examples', [])
            if examples:
                if lang == "ko":
                    console.print("[bold]예시:[/bold]")
                else:
                    console.print("[bold]Examples:[/bold]")
                for example in examples:
                    console.print(f"  [green]{example}[/green]")
                console.print("")

            # Options
            options = help_data.get('options', [])
            if options:
                if lang == "ko":
                    console.print("[bold]옵션:[/bold]")
                else:
                    console.print("[bold]Options:[/bold]")
                for opt_name, opt_desc in options:
                    console.print(f"  [cyan]{opt_name:20}[/cyan] {opt_desc}")
                console.print("")

            # Footer
            if lang == "ko":
                console.print(f"[dim]더 자세한 정보: mhelp {cmd}[/dim]")
                console.print(f"[dim]기본 도움말: {command_name} --help-default[/dim]\n")
            else:
                console.print(f"[dim]More info: mhelp {cmd}[/dim]")
                console.print(f"[dim]Default help: {command_name} --help-default[/dim]\n")

            ctx.exit(0)

    # Fall back to default help if no bilingual content
    console.print(ctx.get_help())
    ctx.exit(0)


def bilingual_help_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Callback for --help option that shows bilingual help."""
    if not value or ctx.resilient_parsing:
        return

    # Get command name from context
    command_name = ctx.info_name or ""
    show_bilingual_help(ctx, command_name)


# Shared app instance
app = typer.Typer(
    name="memory-tool",
    help="Time-Space Integrated Knowledge System",
    add_completion=False,
    rich_markup_mode="rich",
)


# Override app's invoke to intercept --help
_original_invoke = app.__class__.__call__


def _bilingual_invoke(self, *args, **kwargs):
    """Intercept --help calls and show bilingual help."""
    import sys

    # Check if --help is being requested for a subcommand
    if len(sys.argv) >= 3 and sys.argv[2] in ("--help", "-h"):
        command_name = sys.argv[1]

        # Try to show bilingual help
        from memory_tool.commands.help import HELP_CONTENT
        lang = get_help_language()

        if command_name in HELP_CONTENT:
            help_data = HELP_CONTENT[command_name].get(lang, HELP_CONTENT[command_name].get("en", {}))

            if help_data:
                _console = Console()

                # Header
                _console.print(f"\n[bold cyan]{help_data.get('name', command_name)}[/bold cyan]")
                _console.print(f"[dim]{help_data.get('summary', '')}[/dim]\n")

                # Description
                if lang == "ko":
                    _console.print("[bold]설명:[/bold]")
                else:
                    _console.print("[bold]Description:[/bold]")
                _console.print(help_data.get('description', '').strip())
                _console.print("")

                # Examples
                examples = help_data.get('examples', [])
                if examples:
                    if lang == "ko":
                        _console.print("[bold]예시:[/bold]")
                    else:
                        _console.print("[bold]Examples:[/bold]")
                    for example in examples:
                        _console.print(f"  [green]{example}[/green]")
                    _console.print("")

                # Options
                options = help_data.get('options', [])
                if options:
                    if lang == "ko":
                        _console.print("[bold]옵션:[/bold]")
                    else:
                        _console.print("[bold]Options:[/bold]")
                    for opt_name, opt_desc in options:
                        _console.print(f"  [cyan]{opt_name:20}[/cyan] {opt_desc}")
                    _console.print("")

                # Footer
                if lang == "ko":
                    _console.print(f"[dim]더 자세한 정보: mhelp {command_name}[/dim]")
                else:
                    _console.print(f"[dim]More info: mhelp {command_name}[/dim]")
                _console.print("")

                raise SystemExit(0)

    # Fall back to original invoke
    return _original_invoke(self, *args, **kwargs)


# Apply the bilingual help interceptor
app.__class__.__call__ = _bilingual_invoke

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
