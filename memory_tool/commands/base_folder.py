"""Base folder management commands (mbase)."""

import sys
from pathlib import Path

import typer

from memory_tool.commands.common import app, console
from memory_tool.utils.paths import (
    CONTENT_SUBDIRS,
    POINTER_FILENAME,
    ROOT_BASE,
    display_path,
    resolve_base,
)


SOURCE_LABEL = {
    "pointer": f"{POINTER_FILENAME} pointer file",
    "legacy": "legacy .memory/ folder (no pointer file yet)",
    "env": "MEMORY_TOOL_ROOT / MEMORY_TOOL_BASE environment variable",
    "default": "default (nothing initialized here)",
}


def _show(porcelain: bool = False) -> None:
    """Print the resolved base folder and how it was determined.

    Args:
        porcelain: Print only the base folder name, for scripts and the
            Obsidian plugin to consume.
    """
    paths = resolve_base()

    if porcelain:
        # Deliberately plain: one line, no markup, no rich wrapping.
        print(paths.base_name)
        return

    console.print("[cyan]Memory Tool base folder:[/cyan]\n")
    console.print(f"  Project root : {paths.root}")
    console.print(f"  Base folder  : {paths.base}")
    console.print(f"  Base name    : {paths.base_name}")
    console.print(f"  Resolved via : {SOURCE_LABEL.get(paths.source, paths.source)}")
    console.print(f"  Initialized  : {'yes' if paths.found else 'no'}")

    if paths.is_root_base:
        console.print(
            "\n[dim]The project root is the base folder, so records are written "
            "directly to timeline/, modules/, ...[/dim]"
        )
        console.print(
            f"[dim]Only these folders are searched and indexed: "
            f"{', '.join(CONTENT_SUBDIRS)}[/dim]"
        )
    elif paths.is_hidden_base:
        console.print(
            f"\n[yellow]NOTE[/yellow] '{paths.base_name}' starts with a dot, so "
            f"Obsidian hides it."
        )
        console.print(
            "[dim]Use a visible name (mbase set memory) or the vault root "
            "(mbase set .) to work with it in Obsidian.[/dim]"
        )

    if paths.found:
        console.print(f"\n[bold]Content locations:[/bold]")
        for name in CONTENT_SUBDIRS:
            d = paths.base / name
            mark = "[green]OK[/green]" if d.is_dir() else "[dim]--[/dim]"
            console.print(f"  {mark} {display_path(d)}")

    pointer = paths.pointer_file
    console.print(
        f"\n[dim]Pointer file: {pointer}"
        f"{'' if pointer.is_file() else ' (not created yet)'}[/dim]"
    )


def _render_plan(plan, dry_run: bool) -> None:
    """Print a preflight report for a rename plan."""
    header = "Planned changes" if dry_run else "Applying changes"
    old_display = "the project root" if plan.from_root else f"'{plan.old_name}'"
    new_display = "the project root" if plan.to_root else f"'{plan.new_name}'"

    console.print(f"[cyan]{header}:[/cyan] {old_display} -> {new_display}\n")

    console.print(f"[bold]Moves ({len(plan.moves)}):[/bold]")
    if plan.moves:
        for source, target in plan.moves:
            console.print(f"  {display_path(source)}  ->  {display_path(target)}")
    else:
        console.print("  [dim]none[/dim]")

    console.print(
        f"\n[bold]Markdown references to rewrite: "
        f"{plan.rewrite_line_total} line(s) in {len(plan.rewrites)} file(s)[/bold]"
    )
    for rw in plan.rewrites[:15]:
        console.print(f"  {display_path(rw.path)} ({rw.count})")
    if len(plan.rewrites) > 15:
        console.print(f"  [dim]... and {len(plan.rewrites) - 15} more[/dim]")

    if plan.gitignore_edit:
        path, old_line, new_line = plan.gitignore_edit
        console.print(f"\n[bold].gitignore:[/bold] {display_path(path)}")
        console.print(f"  [red]- {old_line.strip()}[/red]")
        console.print(f"  [green]+ {new_line.strip()}[/green]")

    if plan.kb_path_edit:
        old_value, new_value = plan.kb_path_edit
        console.print(f"\n[bold]config kb.path:[/bold]")
        console.print(f"  [red]- {old_value}[/red]")
        console.print(f"  [green]+ {new_value}[/green]")

    console.print(f"\n[bold]Pointer file:[/bold] {POINTER_FILENAME} -> base: \"{plan.new_name}\"")

    if plan.warnings:
        console.print(f"\n[yellow]Warnings:[/yellow]")
        for w in plan.warnings:
            console.print(f"  - {w}")


def _resolve_target_root(root_option: str) -> Path:
    """Decide which project a destructive rename applies to.

    Base folder discovery walks *up* from the working directory, so running
    `mbase set` in an uninitialized folder can silently resolve to an unrelated
    project further up the tree -- including the knowledge base in the user's
    home directory. Because renaming moves files, the target project must be
    unambiguous: either the working directory is the project root, or --root
    names it explicitly.

    Args:
        root_option: Value of the --root option (may be None)

    Returns:
        The project root to operate on.
    """
    if root_option:
        root = Path(root_option).expanduser().resolve()
        if not root.is_dir():
            console.print(f"[red]ERROR[/red] --root is not a directory: {root}")
            sys.exit(1)
        return root

    cwd = Path.cwd().resolve()
    resolved = resolve_base().root.resolve()

    if resolved != cwd:
        console.print(
            f"[red]ERROR[/red] The knowledge base for this directory lives in a "
            f"parent project:"
        )
        console.print(f"  Working directory : {cwd}")
        console.print(f"  Project root      : {resolved}")
        console.print(
            "\n[dim]Renaming moves files, so the target project must be explicit.[/dim]"
        )
        console.print(f'[dim]Confirm with: mbase set <name> --root "{resolved}"[/dim]')
        sys.exit(1)

    return cwd


def _set(
    new_name: str,
    dry_run: bool,
    rewrite: bool,
    rewrite_all: bool,
    update_git: bool,
    yes: bool,
    root_option: str = None,
) -> None:
    """Rename the base folder."""
    from memory_tool.core.rebase import RebaseError, Rebaser

    target_root = _resolve_target_root(root_option)

    try:
        rebaser = Rebaser(target_root)
        plan = rebaser.plan(
            new_name,
            rewrite=rewrite,
            rewrite_all=rewrite_all,
            update_git=update_git,
        )
    except RebaseError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    if not plan.ok:
        console.print("[red]ERROR[/red] Cannot rename the base folder:")
        for err in plan.errors:
            console.print(f"  - {err}")
        sys.exit(1)

    _render_plan(plan, dry_run=dry_run)

    if dry_run:
        console.print("\n[dim]Dry run -- nothing was changed.[/dim]")
        return

    if not yes:
        console.print()
        confirm = typer.confirm("Apply these changes?", default=False)
        if not confirm:
            console.print("[dim]Cancelled -- nothing was changed.[/dim]")
            return

    try:
        result = rebaser.apply(plan)
    except RebaseError as e:
        console.print(f"\n[red]ERROR[/red] {e}")
        sys.exit(1)

    console.print(f"\n[green]OK[/green] Base folder is now '{plan.new_name}'")
    console.print(f"  Moved      : {len(result['moved'])} entr(y/ies)")
    console.print(f"  Rewritten  : {len(result['rewritten'])} file(s)")
    console.print(f"  Pointer    : {display_path(result['pointer'])}")
    if result["gitignore"]:
        console.print(f"  .gitignore : {display_path(result['gitignore'])}")
    if result["kb_path"]:
        console.print(f"  kb.path    : {result['kb_path']}")

    console.print("\n[dim]Verify with: mbase show[/dim]")
    if plan.to_root:
        console.print(
            "[dim]In Obsidian, point your vault at the project root to see "
            "timeline/ and modules/.[/dim]"
        )


@app.command(
    epilog="For detailed help: [bold]mhelp base[/bold]"
)
def base(
    action: str = typer.Argument("show", help="Action: show, set"),
    name: str = typer.Argument(None, help="New base folder name, or '.' for the project root"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    rewrite_all: bool = typer.Option(
        False, "--rewrite-all", help="Rewrite every markdown reference, not just Related Files"
    ),
    no_rewrite: bool = typer.Option(
        False, "--no-rewrite", help="Do not rewrite any markdown references"
    ),
    no_git_update: bool = typer.Option(
        False, "--no-git-update", help="Do not touch .gitignore"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    root: str = typer.Option(
        None, "--root", help="Explicit project root (required when the base lives in a parent project)"
    ),
    porcelain: bool = typer.Option(
        False, "--porcelain", help="With 'show': print only the base folder name"
    ),
):
    """Show or change the knowledge base folder (mbase command).

    The base folder holds timeline/, modules/, concepts/ and config.yaml. Its
    name is recorded in a small pointer file at the project root, so it can be
    renamed without breaking anything.

    Because Obsidian hides dot-prefixed folders, a visible name (or the vault
    root itself) makes the knowledge base usable inside a vault.

    Examples:
        mbase show                    # Where is the base folder, and why
        mbase set memory              # .memory/ -> memory/
        mbase set . --dry-run         # Preview moving content to the project root
        mbase set . --rewrite-all     # Move to root, rewrite all markdown refs
    """
    action = (action or "show").lower()

    if action == "show":
        _show(porcelain=porcelain)
        return

    if action == "set":
        if not name:
            console.print("[red]ERROR[/red] 'mbase set' needs a name.")
            console.print("[dim]Example: mbase set memory   (or: mbase set . )[/dim]")
            sys.exit(1)
        _set(
            new_name=name,
            dry_run=dry_run,
            rewrite=not no_rewrite,
            rewrite_all=rewrite_all,
            update_git=not no_git_update,
            yes=yes,
            root_option=root,
        )
        return

    console.print(f"[red]ERROR[/red] Unknown action: {action}")
    console.print("[dim]Valid actions: show, set[/dim]")
    sys.exit(1)
