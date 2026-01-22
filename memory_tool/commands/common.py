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
    from rich.panel import Panel
    from rich.table import Table

    lang = get_help_language()
    _console = Console()

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
        "노플": "np",
    }
    cmd = cmd_map.get(command_name, command_name)

    if cmd in HELP_CONTENT:
        help_data = HELP_CONTENT[cmd].get(lang, HELP_CONTENT[cmd].get("en", {}))

        if help_data:
            _show_rich_help(_console, help_data, cmd, command_name, lang)
            ctx.exit(0)

    # Fall back to default help if no bilingual content
    _console.print(ctx.get_help())
    ctx.exit(0)


def _show_rich_help(console: Console, help_data: dict, cmd: str, command_name: str, lang: str) -> None:
    """Display help content in Rich Panel format (Typer-style)."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box

    # Usage line
    console.print()
    usage_text = f"Usage: {command_name} [OPTIONS]"
    if help_data.get('options'):
        # Check if there are subcommands vs options
        has_args = any(not opt[0].startswith("-") for opt in help_data['options'])
        if has_args:
            usage_text = f"Usage: {command_name} [OPTIONS] [ARGS]"

    console.print(f" [bold]{usage_text}[/bold]\n")

    # Summary
    console.print(f" {help_data.get('summary', '')}\n")

    # Description
    desc_title = "설명" if lang == "ko" else "Description"
    description = help_data.get('description', '').strip()
    if description:
        console.print(f" [bold]{desc_title}:[/bold]")
        for line in description.split('\n'):
            console.print(f" {line}")
        console.print()

    # Examples panel
    examples = help_data.get('examples', [])
    if examples:
        example_title = "예시" if lang == "ko" else "Examples"
        example_lines = []
        for ex in examples:
            example_lines.append(f"    [green]{ex}[/green]")
        example_content = "\n".join(example_lines)
        console.print(Panel(
            example_content,
            title=f"[bold]{example_title}[/bold]",
            title_align="left",
            border_style="dim",
            box=box.ROUNDED
        ))

    # Options panel
    options = help_data.get('options', [])
    if options:
        opt_title = "옵션" if lang == "ko" else "Options"
        table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        table.add_column("Option", style="cyan", no_wrap=True)
        table.add_column("Description", style="default")

        for opt_name, opt_desc in options:
            table.add_row(opt_name, opt_desc)

        # Add standard options
        help_text = "이 메시지 표시 후 종료" if lang == "ko" else "Show this message and exit."
        table.add_row("--help", help_text)

        console.print(Panel(
            table,
            title=f"[bold]{opt_title}[/bold]",
            title_align="left",
            border_style="dim",
            box=box.ROUNDED
        ))

    # Footer
    console.print()
    if lang == "ko":
        console.print(f" [dim]더 자세한 정보: mhelp {cmd}[/dim]")
    else:
        console.print(f" [dim]More info: mhelp {cmd}[/dim]")
    console.print()


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
    from rich.panel import Panel
    from rich.text import Text

    # Check if --help is being requested for a subcommand
    if len(sys.argv) >= 3 and sys.argv[2] in ("--help", "-h"):
        command_name = sys.argv[1]

        # Special handling for mhelp --help: show both languages
        if command_name == "help":
            _show_mhelp_bilingual()
            raise SystemExit(0)

        # Try to show bilingual help
        from memory_tool.commands.help import HELP_CONTENT
        lang = get_help_language()

        if command_name in HELP_CONTENT:
            help_data = HELP_CONTENT[command_name].get(lang, HELP_CONTENT[command_name].get("en", {}))

            if help_data:
                _console = Console()
                _show_rich_help(_console, help_data, command_name, command_name, lang)
                raise SystemExit(0)

    # Fall back to original invoke
    return _original_invoke(self, *args, **kwargs)


def _show_mhelp_bilingual():
    """Show mhelp --help in both English and Korean with Rich formatting."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _console = Console()

    # English section
    _console.print()
    _console.print(Panel(
        "[bold]mhelp[/bold] - Show detailed help for commands",
        title="[bold cyan]English[/bold cyan]",
        border_style="cyan"
    ))

    _console.print("[bold]Usage:[/bold] mhelp [COMMAND] [OPTIONS]\n")

    _console.print("[bold]Examples:[/bold]")
    examples_en = [
        ("mhelp", "Show command list"),
        ("mhelp record", "Help for record command"),
        ("mhelp search --lang ko", "Help in Korean (this time only)"),
        ("mhelp --set-lang ko", "Permanently set language to Korean"),
        ("mhelp --list", "List all commands"),
        ("mhelp --guide", "Show advanced features guide"),
    ]
    for cmd, desc in examples_en:
        _console.print(f"  [green]{cmd:30}[/green] [dim]# {desc}[/dim]")

    _console.print()

    # Options table (English)
    table_en = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table_en.add_column("Option", style="cyan")
    table_en.add_column("Description")
    table_en.add_row("COMMAND", "Command name to get help for")
    table_en.add_row("--lang, -l TEXT", "Language for this invocation: en, ko")
    table_en.add_row("--set-lang TEXT", "Permanently set default language: en, ko")
    table_en.add_row("--list", "List all commands")
    table_en.add_row("--guide", "Show advanced features guide")
    table_en.add_row("--help", "Show this message")

    _console.print(Panel(table_en, title="[bold]Options[/bold]", border_style="dim"))

    # Korean section
    _console.print()
    _console.print(Panel(
        "[bold]mhelp[/bold] - 명령어 상세 도움말 표시",
        title="[bold cyan]한국어[/bold cyan]",
        border_style="cyan"
    ))

    _console.print("[bold]사용법:[/bold] mhelp [명령어] [옵션]\n")

    _console.print("[bold]예시:[/bold]")
    examples_ko = [
        ("mhelp", "명령어 목록 표시"),
        ("mhelp record", "record 명령어 도움말"),
        ("mhelp search --lang ko", "한국어로 도움말 (일회성)"),
        ("mhelp --set-lang ko", "기본 언어를 한국어로 영구 설정"),
        ("mhelp --list", "모든 명령어 나열"),
        ("mhelp --guide", "고급 기능 가이드 표시"),
    ]
    for cmd, desc in examples_ko:
        _console.print(f"  [green]{cmd:30}[/green] [dim]# {desc}[/dim]")

    _console.print()

    # Options table (Korean)
    table_ko = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table_ko.add_column("옵션", style="cyan")
    table_ko.add_column("설명")
    table_ko.add_row("명령어", "도움말을 볼 명령어 이름")
    table_ko.add_row("--lang, -l TEXT", "이번 호출의 언어: en, ko")
    table_ko.add_row("--set-lang TEXT", "기본 언어 영구 설정: en, ko")
    table_ko.add_row("--list", "모든 명령어 나열")
    table_ko.add_row("--guide", "고급 기능 가이드 표시")
    table_ko.add_row("--help", "이 메시지 표시")

    _console.print(Panel(table_ko, title="[bold]옵션[/bold]", border_style="dim"))
    _console.print()


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
