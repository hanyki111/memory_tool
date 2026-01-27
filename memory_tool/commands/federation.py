"""CLI commands for Federated Knowledge System.

Commands:
- publish: Publish local module to KB
- import_kb: Import module from KB to local project
"""

from pathlib import Path
from typing import Optional, List

import typer
from rich.table import Table

from memory_tool.commands.common import app, console
from memory_tool.core.federation import Publisher, Importer, Registry
from memory_tool.utils.config import Config


@app.command("publish")
def publish(
    module_name: str = typer.Argument(..., help="Module name to publish"),
    category: str = typer.Option(
        "Projects",
        "--category", "-c",
        help="KB category (Projects or Topics)"
    ),
    tags: Optional[str] = typer.Option(
        None,
        "--tags", "-t",
        help="Comma-separated tags (e.g., search,fts5)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="Preview without making changes"
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Force republish even if unchanged"
    ),
):
    """Publish a local module to Knowledge Base.

    Examples:
        mpublish search-system                    # Publish module
        mpublish search-system --category Topics  # Publish to Topics/
        mpublish search-system --tags search,fts  # Add tags
        mpublish search-system --dry-run          # Preview
        mpublish search-system --force            # Force republish
    """
    # Find .memory path
    memory_path = Path.cwd() / ".memory"
    if not memory_path.exists():
        console.print("[red]Error:[/red] .memory/ not found. Run 'minit' first.")
        raise typer.Exit(1)

    # Find KB path from config
    config = Config(memory_path)
    kb_path = config.get_kb_path()
    if not kb_path:
        console.print("[red]Error:[/red] KB path not configured.")
        console.print("Set with: [cyan]mconfig set kb.path ~/your/kb/path[/cyan]")
        raise typer.Exit(1)

    if not kb_path.exists():
        console.print(f"[red]Error:[/red] KB path does not exist: {kb_path}")
        console.print(f"Create with: [cyan]mkdir -p {kb_path}[/cyan]")
        raise typer.Exit(1)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    # Initialize publisher and publish
    publisher = Publisher(memory_path, kb_path)
    result = publisher.publish(
        module_name=module_name,
        category=category,
        tags=tag_list,
        force=force,
        dry_run=dry_run,
    )

    # Display result
    if result["success"]:
        action = result["action"]
        if action == "dry_run":
            console.print(f"[cyan][DRY RUN][/cyan] {result['message']}")
            console.print(f"  Hash: {result.get('source_hash', 'N/A')}")
            console.print(f"  Version: {result.get('version', 'N/A')}")
            if result.get("files_to_publish"):
                console.print("  Files:")
                for f in result["files_to_publish"]:
                    console.print(f"    - {f}")
        elif action == "unchanged":
            console.print(f"[yellow]{result['message']}[/yellow]")
        else:
            console.print(f"[green]{result['message']}[/green]")
            console.print(f"  Hash: {result.get('source_hash', 'N/A')}")
            console.print(f"  KB path: {result.get('kb_path', 'N/A')}")
            if result.get("files_published"):
                console.print(f"  Files: {len(result['files_published'])}")
    else:
        console.print(f"[red]Error:[/red] {result['message']}")
        raise typer.Exit(1)


@app.command("import-kb")
def import_kb(
    kb_module_path: Optional[str] = typer.Argument(
        None,
        help="KB module path (e.g., Projects/memory-tool/search-system)"
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target", "-t",
        help="Local target path (e.g., ref/search-system)"
    ),
    list_modules: bool = typer.Option(
        False,
        "--list", "-l",
        help="List available KB modules"
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category", "-c",
        help="Filter by category when listing"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project", "-p",
        help="Filter by project when listing"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="Preview without making changes"
    ),
):
    """Import a module from Knowledge Base to local project.

    Examples:
        mimport --list                                   # List KB modules
        mimport --list --category Topics                 # Filter by category
        mimport Projects/memory-tool/search-system       # Import module
        mimport Projects/memory-tool/search-system --target ref/search  # Custom path
    """
    # Find .memory path
    memory_path = Path.cwd() / ".memory"
    if not memory_path.exists():
        console.print("[red]Error:[/red] .memory/ not found. Run 'minit' first.")
        raise typer.Exit(1)

    # Find KB path from config
    config = Config(memory_path)
    kb_path = config.get_kb_path()
    if not kb_path:
        console.print("[red]Error:[/red] KB path not configured.")
        console.print("Set with: [cyan]mconfig set kb.path ~/your/kb/path[/cyan]")
        raise typer.Exit(1)

    if not kb_path.exists():
        console.print(f"[red]Error:[/red] KB path does not exist: {kb_path}")
        raise typer.Exit(1)

    # Initialize importer
    importer = Importer(memory_path, kb_path)

    # List mode
    if list_modules:
        modules = importer.list_available(project=project, category=category)

        if not modules:
            console.print("[yellow]No modules found in KB.[/yellow]")
            return

        table = Table(title="KB Modules")
        table.add_column("Module Path", style="cyan")
        table.add_column("Project", style="green")
        table.add_column("Version", justify="right")
        table.add_column("Tags")
        table.add_column("Published")

        for mod in modules:
            tags_str = ", ".join(mod.tags) if mod.tags else "-"
            published = mod.published_at[:10] if mod.published_at else "-"
            table.add_row(
                mod.kb_path.replace("modules/", ""),
                mod.origin_project,
                str(mod.version),
                tags_str,
                published,
            )

        console.print(table)
        return

    # Import mode
    if not kb_module_path:
        console.print("[red]Error:[/red] Specify a module path or use --list")
        raise typer.Exit(1)

    result = importer.import_module(
        kb_module_path=kb_module_path,
        target_path=target,
        dry_run=dry_run,
    )

    # Display result
    if result["success"]:
        if result["action"] == "dry_run":
            console.print(f"[cyan][DRY RUN][/cyan] {result['message']}")
            if result.get("files_to_import"):
                console.print("  Files:")
                for f in result["files_to_import"]:
                    console.print(f"    - {f}")
        else:
            console.print(f"[green]{result['message']}[/green]")
            console.print(f"  Target: {result.get('target_path', 'N/A')}")
    else:
        console.print(f"[red]Error:[/red] {result['message']}")
        raise typer.Exit(1)
