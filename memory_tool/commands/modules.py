"""Module management CLI commands."""

import sys
from pathlib import Path
from typing import Optional

import typer

from memory_tool.commands.common import (
    app, console, opt_str, arg_str, resolve_module_name
)
from memory_tool.core.module import ModuleManager, ModuleError
from memory_tool.llm.client import LLMClient
from memory_tool.utils.paths import display_path, get_base_path


@app.command()
def module(
    action: str = typer.Argument(..., help="Action: create, list, tree, rename, relink, merge-templates, archive, unarchive, migrate, connections, graph, rebuild-graph, check-links, suggest-links, suggest-ai, ai-organize, auto-tag, graph-history, graph-diff, graph-snapshot, from-text"),
    name: str = typer.Argument(None, help="Module name or path (e.g., 'projects/website')"),
    description: str = typer.Option("", "--desc", "-d", help="Module description"),
    reason: str = typer.Option("", "--reason", "-r", help="Reason for archiving"),
    to: Optional[str] = typer.Option(None, "--to", help="New name for rename action"),
    tags: str = typer.Option("", "--tags", "-t", help="Module tags (comma-separated)"),
    archived: bool = typer.Option(False, "--archived", "-a", help="Include archived modules in list"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Export format: mermaid, graphviz, json (for graph action)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (for graph action)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output (for rebuild-graph in hooks)"),
    version1: int = typer.Option(None, "--v1", help="First version ID (for graph-diff)"),
    version2: int = typer.Option(None, "--v2", help="Second version ID (for graph-diff)"),
    notes: str = typer.Option("", "--notes", "-n", help="Notes for graph snapshot"),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit number of results"),
    text: Optional[str] = typer.Option(None, "--text", help="Input text for from-text action"),
    text_file: Optional[str] = typer.Option(None, "--text-file", help="File path containing input text for from-text action"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview generated module without saving (for from-text action)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing (for relink/merge-templates)"),
    remove: bool = typer.Option(False, "--remove", help="Delete the merged-from directories (for merge-templates)"),
    lang: Optional[str] = typer.Option(None, "--lang", help="Output language for from-text: 'ko', 'en', 'auto'"),
    structure: Optional[str] = typer.Option(None, "--structure", "-s", help="Module structure type for from-text: 'feature' (software), 'topic' (learning/KB), 'auto'"),
    kind: Optional[str] = typer.Option(None, "--kind", "-k", help="Template kind for create: 'knowledge' or 'implementation'"),
    nature: Optional[str] = typer.Option(None, "--nature", help="Body outline for knowledge modules: concept, reference, analysis, tracker, method"),
):
    """Manage modules (supports single-file modules, hierarchical paths, wiki-style [[connections]], and AI suggestions)."""
    action = arg_str(action)
    name = opt_str(name)
    format = opt_str(format)
    output = opt_str(output)

    manager = ModuleManager()

    try:
        if action.lower() == "create":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for create")
                console.print("[dim]Usage: module create <name> [--desc \"description\"][/dim]")
                sys.exit(1)

            tag_list = [t.strip() for t in tags.split(",")] if tags else []
            kind_opt = opt_str(kind)
            nature_opt = opt_str(nature)

            console.print(f"[cyan]Creating module '{name}'...[/cyan]")
            module_path = manager.create(
                name, description, tag_list, kind=kind_opt, nature=nature_opt
            )

            rel_path = display_path(module_path)
            console.print(f"\n[green]OK[/green] Single-file module created: {name}")
            console.print(f"[dim]File location: {rel_path}[/dim]")

            if kind_opt or nature_opt:
                label = kind_opt or "knowledge"
                if nature_opt:
                    label += f" / {nature_opt}"
                console.print(f"[dim]Template: {label}[/dim]")
            else:
                console.print(
                    "[dim]Tip: --kind knowledge|implementation applies the MOP "
                    "templates. See 'mhelp module'.[/dim]"
                )

            try:
                from memory_tool.utils.suggestion_helper import check_and_suggest_after_command
                memory_dir = get_base_path()
                check_and_suggest_after_command(memory_dir, "module", force=False)
            except Exception:
                pass

        elif action.lower() == "migrate":
            if name:
                resolved_name = resolve_module_name(name)
                console.print(f"[cyan]Migrating module '{resolved_name}' to single file...[/cyan]")
                res = manager.migrate_module(resolved_name)
                console.print(f"[green]OK[/green] Migrated module: [bold]{res}[/bold]")
            else:
                console.print("[cyan]Migrating all legacy multi-file modules to single-file format...[/cyan]")
                migrated = manager.migrate_all_modules()
                console.print(f"\n[green]OK[/green] Successfully migrated {len(migrated)} modules:")
                for m in migrated:
                    console.print(f"  - {m}")

        elif action.lower() == "relink":
            # Repairs links after a module is moved in Obsidian or a file
            # manager. Discovery already finds the module at its new location;
            # what breaks is every [[old/path]] still aimed at the old one, and
            # a broken wiki link renders as plain text rather than an error.
            from memory_tool.core.relink import apply_plan, build_plan, format_plan

            console.print("[cyan]Scanning module links...[/cyan]")
            plan = build_plan(manager)

            if plan.is_empty:
                console.print("[green]OK[/green] No broken module links found.")
            else:
                if plan.proposals:
                    apply_plan(plan, dry_run=dry_run)

                console.print()
                # markup=False: the report is full of [[links]], which Rich
                # would otherwise parse as style tags and swallow.
                console.print(format_plan(plan, dry_run=dry_run), markup=False)

                if plan.proposals and not dry_run:
                    # The graph is a cache of the links just rewritten, so it is
                    # stale the moment they change.
                    try:
                        from memory_tool.core.connections import ConnectionGraph

                        count = ConnectionGraph().rebuild_from_modules()
                        console.print(
                            f"\n[green]OK[/green] Connection graph rebuilt ({count} links)."
                        )
                    except Exception as exc:
                        console.print(
                            f"\n[yellow]WARNING[/yellow] Links repaired but the graph "
                            f"rebuild failed: {exc}\n"
                            f"[dim]Run 'mmodule rebuild-graph' to retry.[/dim]"
                        )

                if plan.proposals and dry_run:
                    console.print("\n[dim]Nothing written. Re-run without --dry-run to apply.[/dim]")

                if plan.unresolved:
                    console.print(
                        "\n[dim]Unresolved links are left untouched -- rename the target "
                        "or fix the link by hand.[/dim]"
                    )

        elif action.lower() == "merge-templates":
            # `migrate` consolidates a *module*'s files; template sets are a
            # different shape (they carry a natures menu that is never emitted)
            # and live outside modules/, so they need their own pass.
            import shutil

            from memory_tool.core.module_templates import (
                KINDS,
                TemplateError as _TemplateError,
                merge_template_dir,
                single_file_name,
            )

            templates_dir = get_base_path() / "templates"
            merged_any = False

            for kind in KINDS:
                source = templates_dir / kind
                if not source.is_dir():
                    continue

                target = templates_dir / single_file_name(kind)

                try:
                    merged = merge_template_dir(source)
                except _TemplateError as exc:
                    console.print(f"[yellow]SKIP[/yellow] {kind}: {exc}")
                    continue

                merged_any = True
                rel = display_path(target)

                if dry_run:
                    console.print(
                        f"[cyan]Would merge[/cyan] {display_path(source)}/ "
                        f"-> {rel} ({len(merged)} bytes)"
                    )
                    continue

                target.write_text(merged, encoding="utf-8")
                console.print(f"[green]OK[/green] Merged {kind} -> {rel}")

                if remove:
                    shutil.rmtree(source)
                    console.print(f"[dim]Removed {display_path(source)}/[/dim]")

            if not merged_any:
                console.print(
                    "[dim]No template directories found under "
                    f"{display_path(templates_dir)}. Nothing to merge.[/dim]"
                )
            elif dry_run:
                console.print("\n[dim]Nothing written. Re-run without --dry-run to apply.[/dim]")
            elif not remove:
                console.print(
                    "\n[dim]The single file now takes precedence. Re-run with "
                    "--remove to delete the directories it was built from.[/dim]"
                )

        elif action.lower() == "list":
            modules = manager.list_modules(include_archived=archived)

            active = modules.get("active", [])
            console.print(f"[cyan]Active Modules:[/cyan] {len(active)}\n")

            if active:
                for mod_name in active:
                    console.print(f"  - {mod_name}")
            else:
                console.print("  [dim]No active modules[/dim]")

            if archived and "archived" in modules:
                arch = modules["archived"]
                console.print(f"\n[cyan]Archived Modules:[/cyan] {len(arch)}\n")

                if arch:
                    for mod_name in arch:
                        console.print(f"  - {mod_name}")
                else:
                    console.print("  [dim]No archived modules[/dim]")

        elif action.lower() == "archive":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for archive")
                console.print("[dim]Usage: module archive <name> [--reason \"reason\"][/dim]")
                sys.exit(1)

            resolved_name = resolve_module_name(name)

            console.print(f"[cyan]Archiving module '{resolved_name}'...[/cyan]")
            archive_path = manager.archive(resolved_name, reason)

            rel_path = display_path(archive_path)
            console.print(f"\n[green]OK[/green] Module archived: {resolved_name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")

            if reason:
                console.print(f"[dim]Reason: {reason}[/dim]")

        elif action.lower() == "tree":
            tree = manager.build_module_tree()

            if not tree:
                console.print("[dim]No modules found[/dim]")
                return

            console.print("[cyan]Module Hierarchy:[/cyan]\n")

            def print_tree(node_dict, prefix="", is_last=True):
                items = list(node_dict.items())
                for i, (node_name, children) in enumerate(items):
                    is_last_item = (i == len(items) - 1)
                    connector = "└── " if is_last_item else "├── "
                    console.print(f"{prefix}{connector}{node_name}")
                    if children:
                        extension = "    " if is_last_item else "│   "
                        print_tree(children, prefix + extension, is_last_item)

            print_tree(tree)

        elif action.lower() == "rename":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for rename")
                console.print("[dim]Usage: module rename <name> --to <new-name>[/dim]")
                sys.exit(1)

            new_name = opt_str(to)
            if not new_name:
                console.print("[red]ERROR[/red] New name is required for rename")
                console.print("[dim]Usage: module rename <name> --to <new-name>[/dim]")
                sys.exit(1)

            resolved_name = resolve_module_name(name)

            console.print(f"[cyan]Renaming module '{resolved_name}' -> '{new_name}'...[/cyan]")
            new_path = manager.rename(resolved_name, new_name)

            rel_path = display_path(new_path)
            console.print(f"\n[green]OK[/green] Module renamed: {resolved_name} -> {new_name}")
            console.print(f"[dim]New location: {rel_path}[/dim]")

        elif action.lower() == "connections":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for connections")
                console.print("[dim]Usage: module connections <name>[/dim]")
                sys.exit(1)

            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()
            outgoing = graph.get_outgoing_connections(name)
            incoming = graph.get_incoming_connections(name)

            console.print(f"[cyan]Connections for module:[/cyan] {name}\n")

            if outgoing:
                console.print(f"[green]Outgoing ({len(outgoing)}):[/green]")
                for conn in outgoing:
                    console.print(f"  → {conn.target}")
                    console.print(f"    [dim]{conn.source_file}:{conn.line_number}[/dim]")
            else:
                console.print("[dim]No outgoing connections[/dim]")

            console.print()

            if incoming:
                console.print(f"[green]Incoming ({len(incoming)}):[/green]")
                for conn in incoming:
                    console.print(f"  ← {conn.source}")
                    console.print(f"    [dim]{conn.source_file}:{conn.line_number}[/dim]")
            else:
                console.print("[dim]No incoming connections[/dim]")

        elif action.lower() == "graph":
            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()

            if format:
                if format.lower() == "mermaid":
                    diagram = graph.export_mermaid()
                    if output:
                        output_path = Path(output)
                        output_path.write_text(diagram, encoding="utf-8")
                        console.print(f"[green]OK[/green] Mermaid diagram saved to: {output}")
                    else:
                        console.print("[cyan]Mermaid Diagram:[/cyan]\n")
                        console.print(diagram)

                elif format.lower() == "graphviz":
                    dot = graph.export_graphviz()
                    if output:
                        output_path = Path(output)
                        output_path.write_text(dot, encoding="utf-8")
                        console.print(f"[green]OK[/green] Graphviz DOT saved to: {output}")
                    else:
                        console.print("[cyan]Graphviz DOT:[/cyan]\n")
                        console.print(dot)

                elif format.lower() == "json":
                    import json
                    graph_data = graph.to_json()
                    json_output = json.dumps(graph_data, indent=2, ensure_ascii=False)
                    if output:
                        output_path = Path(output)
                        output_path.write_text(json_output, encoding="utf-8")
                        console.print(f"[green]OK[/green] JSON saved to: {output}")
                    else:
                        print(json_output)

                else:
                    console.print(f"[red]ERROR[/red] Unknown format: {format}")
                    console.print("Valid formats: mermaid, graphviz, json")
                    sys.exit(1)

                return

            stats = graph.get_graph_stats()

            console.print("[cyan]Module Connection Graph[/cyan]\n")
            console.print(f"Total connections: {stats['total_connections']}")
            console.print(f"Connected modules: {stats['connected_modules']}")
            console.print(f"Orphaned modules: {stats['orphaned_modules']}")

            all_modules = graph.get_all_modules()

            if all_modules:
                console.print(f"\n[cyan]Module Connections:[/cyan]\n")
                for mod in sorted(all_modules):
                    outgoing = graph.get_outgoing_connections(mod)
                    incoming = graph.get_incoming_connections(mod)
                    out_count = len(outgoing)
                    in_count = len(incoming)
                    console.print(f"  {mod}")
                    console.print(f"    [dim]→ {out_count} outgoing, ← {in_count} incoming[/dim]")
            else:
                console.print("\n[dim]No connections found. Run 'module rebuild-graph' to build the graph.[/dim]")

        elif action.lower() == "check-links":
            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()
            console.print("[cyan]Checking module links...[/cyan]\n")

            broken = graph.check_broken_links()

            if broken:
                console.print(f"[yellow]Found {len(broken)} module(s) with broken links:[/yellow]\n")
                for source, targets in sorted(broken.items()):
                    console.print(f"  {source}:")
                    for target in targets:
                        console.print(f"    [red]x[/red] [[{target}]] -> module not found")
                console.print()
            else:
                console.print("[green]OK[/green] No broken links found\n")

            orphaned = graph.get_orphaned_modules()

            if orphaned:
                console.print(f"[yellow]Found {len(orphaned)} orphaned module(s) (no connections):[/yellow]\n")
                for mod in sorted(orphaned):
                    console.print(f"  [dim]{mod}[/dim]")
                console.print()
            else:
                console.print("[green]OK[/green] No orphaned modules")

        elif action.lower() == "suggest-links":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for suggest-links")
                console.print("[dim]Usage: module suggest-links <name>[/dim]")
                sys.exit(1)

            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()
            console.print(f"[cyan]Suggesting links for:[/cyan] {name}\n")

            suggestions = graph.suggest_backlinks(name, max_suggestions=10)

            if suggestions:
                console.print(f"[green]Suggested connections ({len(suggestions)}):[/green]\n")
                for mod, reason_text in suggestions:
                    console.print(f"  → [[{mod}]]")
                    console.print(f"    [dim]{reason_text}[/dim]")
                    console.print()
                console.print("[dim]Add these links to your module's .md files to create connections.[/dim]")
            else:
                console.print("[dim]No suggestions found.[/dim]")
                console.print("[dim]This module may already be well-connected, or there are no related modules.[/dim]")

        elif action.lower() == "rebuild-graph":
            from memory_tool.core.connections import ConnectionGraph
            from memory_tool.core.graph_versions import GraphVersionManager

            if not quiet:
                console.print("[cyan]Rebuilding connection graph...[/cyan]")

            graph = ConnectionGraph()

            try:
                total = graph.rebuild_from_modules()

                if not quiet:
                    console.print(f"\n[green]OK[/green] Connection graph rebuilt")
                    console.print(f"Found {total} connections")
                    stats = graph.get_graph_stats()
                    console.print(f"Connected modules: {stats['connected_modules']}")
                    console.print(f"Orphaned modules: {stats['orphaned_modules']}")

                try:
                    version_manager = GraphVersionManager()
                    version_id = version_manager.create_snapshot(notes="Auto-snapshot after rebuild-graph")
                    if not quiet:
                        console.print(f"\n[dim]Auto-snapshot created (version {version_id})[/dim]")
                except Exception:
                    pass

            except Exception as e:
                if not quiet:
                    console.print(f"[red]ERROR[/red] Failed to rebuild graph: {e}")
                sys.exit(1)

        elif action.lower() == "suggest-ai":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for suggest-ai")
                console.print("[dim]Usage: module suggest-ai <name>[/dim]")
                sys.exit(1)

            if not LLMClient.check_availability():
                console.print("[red]ERROR[/red] LLM not configured")
                console.print("[dim]Set ANTHROPIC_API_KEY environment variable or configure Ollama[/dim]")
                console.print("[dim]See config.yaml for LLM configuration[/dim]")
                sys.exit(1)

            from memory_tool.core.ai_suggester import AIConnectionSuggester

            console.print(f"[cyan]Analyzing module content for AI suggestions:[/cyan] {name}\n")
            console.print("[dim]Using LLM to analyze content similarity...[/dim]\n")

            mod_manager = ModuleManager()
            module_path = mod_manager.modules_path / name

            if not module_path.exists():
                console.print(f"[red]ERROR[/red] Module not found: {name}")
                sys.exit(1)

            all_modules = mod_manager.discover_all_modules()
            candidates = [
                (str(mod), mod_manager.modules_path / mod)
                for mod in all_modules
                if str(mod) != name
            ]

            suggester = AIConnectionSuggester()
            try:
                suggestions = suggester.suggest_connections(
                    module_path,
                    candidates,
                    max_suggestions=5
                )

                if suggestions:
                    console.print(f"[green]AI-suggested connections ({len(suggestions)}):[/green]\n")
                    for module_name_sug, reason_text, confidence in suggestions:
                        confidence_pct = int(confidence * 100)
                        color = "green" if confidence >= 0.7 else "yellow" if confidence >= 0.5 else "dim"
                        display_name = module_name_sug.replace('\\', '/')
                        console.print(f"  → \\[\\[{display_name}]] [{color}]({confidence_pct}%)[/{color}]")
                        console.print(f"    [dim]{reason_text}[/dim]")
                        console.print()
                    console.print("[dim]Add these links to your module's .md files to create connections.[/dim]")
                else:
                    console.print("[dim]No strong connections suggested by AI.[/dim]")
                    console.print("[dim]The module content may be too unique or general.[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] AI suggestion failed: {e}")
                sys.exit(1)

        elif action.lower() == "ai-organize":
            from memory_tool.core.ai_organizer import ModuleOrganizer

            console.print("[cyan]Analyzing module structure...[/cyan]\n")

            mod_manager = ModuleManager()
            organizer = ModuleOrganizer(mod_manager.modules_path)

            try:
                scope = name if name else None
                include_merges = True

                with console.status("[dim]Analyzing modules (this may take a moment)...[/dim]"):
                    suggestions = organizer.analyze_and_suggest(
                        scope=scope,
                        include_merges=include_merges
                    )

                if suggestions:
                    output_text = organizer.format_suggestions(suggestions)
                    console.print(output_text)
                    console.print(f"\n[dim]Total suggestions: {len(suggestions)}[/dim]")
                    console.print("[dim]Use these suggestions to improve your module organization.[/dim]")
                else:
                    console.print("[green]✓ Module structure looks good![/green]")
                    console.print("[dim]No organization suggestions at this time.[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Analysis failed: {e}")
                sys.exit(1)

        elif action.lower() == "auto-tag":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for auto-tag")
                console.print("[dim]Usage: module auto-tag <name>[/dim]")
                sys.exit(1)

            if not LLMClient.check_availability():
                console.print("[red]ERROR[/red] LLM not configured")
                console.print("[dim]Set ANTHROPIC_API_KEY environment variable or configure Ollama[/dim]")
                console.print("[dim]See config.yaml for LLM configuration[/dim]")
                sys.exit(1)

            from memory_tool.core.ai_suggester import AIConnectionSuggester

            console.print(f"[cyan]Analyzing module content for tags:[/cyan] {name}\n")
            console.print("[dim]Using LLM to generate relevant tags...[/dim]\n")

            mod_manager = ModuleManager()
            module_path = mod_manager.modules_path / name

            if not module_path.exists():
                console.print(f"[red]ERROR[/red] Module not found: {name}")
                sys.exit(1)

            suggester = AIConnectionSuggester()
            try:
                tag_suggestions = suggester.suggest_tags(module_path, max_tags=5)

                if tag_suggestions:
                    console.print(f"[green]Suggested tags ({len(tag_suggestions)}):[/green]\n")
                    for tag in tag_suggestions:
                        console.print(f"  • {tag}")
                    console.print(f"\n[dim]Add these tags to your module's metadata or use them for organization.[/dim]")
                else:
                    console.print("[dim]No tags suggested by AI.[/dim]")
                    console.print("[dim]The module may need more content for tag generation.[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Tag generation failed: {e}")
                sys.exit(1)

        elif action.lower() == "graph-snapshot":
            from memory_tool.core.graph_versions import GraphVersionManager

            console.print("[cyan]Creating graph snapshot...[/cyan]")

            manager_ver = GraphVersionManager()

            try:
                version_id = manager_ver.create_snapshot(notes=notes or "")

                console.print(f"\n[green]OK[/green] Snapshot created")
                console.print(f"Version ID: {version_id}")
                if notes:
                    console.print(f"Notes: {notes}")

                version = manager_ver.get_version(version_id)
                if version:
                    console.print(f"Connections: {version.total_connections}")
                    console.print(f"Modules: {version.total_modules}")
                    console.print(f"Timestamp: {version.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Failed to create snapshot: {e}")
                sys.exit(1)

        elif action.lower() == "graph-history":
            from memory_tool.core.graph_versions import GraphVersionManager

            console.print("[cyan]Graph Version History[/cyan]\n")

            manager_ver = GraphVersionManager()

            try:
                versions = manager_ver.list_versions(limit=limit or 10)

                if versions:
                    console.print(f"[green]Recent versions ({len(versions)}):[/green]\n")
                    for ver in versions:
                        timestamp_str = ver.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        console.print(f"  Version {ver.version_id} - {timestamp_str}")
                        console.print(f"    Connections: {ver.total_connections}, Modules: {ver.total_modules}")
                        if ver.notes:
                            console.print(f"    Notes: [dim]{ver.notes}[/dim]")
                        console.print()

                    total_count = manager_ver.get_version_count()
                    if total_count > len(versions):
                        console.print(f"[dim]Showing {len(versions)} of {total_count} total versions[/dim]")
                        console.print(f"[dim]Use --limit to see more versions[/dim]")
                else:
                    console.print("[dim]No versions found.[/dim]")
                    console.print("[dim]Create a snapshot with: module graph-snapshot[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Failed to list versions: {e}")
                sys.exit(1)

        elif action.lower() == "graph-diff":
            if not version1 or not version2:
                console.print("[red]ERROR[/red] Two version IDs required for graph-diff")
                console.print("[dim]Usage: module graph-diff --version1 <id> --version2 <id>[/dim]")
                sys.exit(1)

            from memory_tool.core.graph_versions import GraphVersionManager

            console.print(f"[cyan]Comparing graph versions {version1} → {version2}[/cyan]\n")

            manager_ver = GraphVersionManager()

            try:
                v1 = manager_ver.get_version(version1)
                v2 = manager_ver.get_version(version2)

                if not v1:
                    console.print(f"[red]ERROR[/red] Version {version1} not found")
                    sys.exit(1)
                if not v2:
                    console.print(f"[red]ERROR[/red] Version {version2} not found")
                    sys.exit(1)

                console.print(f"[dim]Version {version1}:[/dim] {v1.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                console.print(f"  Connections: {v1.total_connections}, Modules: {v1.total_modules}")
                console.print()
                console.print(f"[dim]Version {version2}:[/dim] {v2.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                console.print(f"  Connections: {v2.total_connections}, Modules: {v2.total_modules}")
                console.print()

                diff = manager_ver.diff_versions(version1, version2)

                if diff["added"]:
                    console.print(f"[green]Added connections ({len(diff['added'])}):[/green]")
                    for source, target in diff["added"][:10]:
                        console.print(f"  + {source} → {target}")
                    if len(diff["added"]) > 10:
                        console.print(f"  [dim]... and {len(diff['added']) - 10} more[/dim]")
                    console.print()

                if diff["removed"]:
                    console.print(f"[red]Removed connections ({len(diff['removed'])}):[/red]")
                    for source, target in diff["removed"][:10]:
                        console.print(f"  - {source} → {target}")
                    if len(diff["removed"]) > 10:
                        console.print(f"  [dim]... and {len(diff['removed']) - 10} more[/dim]")
                    console.print()

                if not diff["added"] and not diff["removed"]:
                    console.print("[dim]No changes between versions[/dim]")

                console.print(f"[dim]Summary: +{len(diff['added'])} -{len(diff['removed'])} ={len(diff['unchanged'])}[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Failed to compare versions: {e}")
                sys.exit(1)

        elif action.lower() == "unarchive":
            if not name:
                console.print("[red]ERROR[/red] Module name is required for unarchive")
                console.print("[dim]Usage: module unarchive <name>[/dim]")
                sys.exit(1)

            console.print(f"[cyan]Restoring module '{name}' from archive...[/cyan]")
            module_path = manager.unarchive(name)

            rel_path = display_path(module_path)
            console.print(f"\n[green]OK[/green] Module restored: {name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")

        elif action.lower() == "from-text":
            from memory_tool.core.ai_module_generator import AIModuleGenerator

            input_text = None

            if text:
                input_text = text
            elif text_file:
                text_path = Path(text_file)
                if not text_path.exists():
                    console.print(f"[red]ERROR[/red] Text file not found: {text_file}")
                    sys.exit(1)
                input_text = text_path.read_text(encoding="utf-8")
            else:
                console.print("[red]ERROR[/red] Either --text or --text-file is required")
                console.print("[dim]Usage: module from-text --text \"Your text here\"[/dim]")
                console.print("[dim]   or: module from-text --text-file input.txt[/dim]")
                sys.exit(1)

            if not input_text.strip():
                console.print("[red]ERROR[/red] Input text is empty")
                sys.exit(1)

            if not LLMClient.check_availability():
                console.print("[red]ERROR[/red] LLM not configured")
                console.print("[dim]Set ANTHROPIC_API_KEY environment variable or configure Ollama[/dim]")
                sys.exit(1)

            structure_type = structure if structure else "auto"
            if structure_type not in ["feature", "topic", "auto"]:
                console.print(f"[red]ERROR[/red] Invalid structure type: {structure_type}")
                console.print("[dim]Valid values: 'feature', 'topic', 'auto'[/dim]")
                sys.exit(1)

            console.print("[cyan]Analyzing text and generating module structure...[/cyan]")
            if structure_type != "auto":
                structure_label = "Feature-based" if structure_type == "feature" else "Topic-based"
                console.print(f"[dim]Structure type: {structure_label} (forced)[/dim]")

            try:
                generator = AIModuleGenerator()
                output_lang = lang if lang else "auto"

                with console.status("[dim]Generating module (this may take a moment)...[/dim]"):
                    generated = generator.generate(input_text, language=output_lang, structure_type=structure_type)

                if preview:
                    console.print()
                    preview_output = generator.format_preview(generated)
                    console.print(preview_output)
                    console.print()
                    console.print("[yellow]Preview mode:[/yellow] Module not saved")
                    console.print(f"[dim]To save, run without --preview flag[/dim]")
                else:
                    module_path = generator.save_module(generated)
                    rel_path = display_path(module_path)

                    structure_label = "Feature-based" if generated.structure_type == "feature" else "Topic-based"
                    console.print(f"\n[green]OK[/green] Module created: {generated.name}")
                    console.print(f"[dim]Location: {rel_path}[/dim]")
                    console.print(f"[dim]Structure: {structure_label}[/dim]")
                    console.print(f"[dim]Type: {generated.module_type}[/dim]")

                    if generated.suggested_connections:
                        console.print(f"\n[cyan]Suggested connections:[/cyan]")
                        for conn in generated.suggested_connections:
                            console.print(f"  - [[{conn}]]")

                    console.print(f"\n[dim]Files created:[/dim]")
                    console.print(f"  - module.md      (module definition)")
                    console.print(f"  - current.md     (current status)")
                    console.print(f"  - decisions.md   (decisions)")
                    if generated.suggested_connections:
                        console.print(f"  - dependencies.md (dependencies)")

            except ValueError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]ERROR[/red] Module generation failed: {e}")
                sys.exit(1)

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("Valid actions: create, list, tree, archive, unarchive, connections, graph, rebuild-graph,")
            console.print("  check-links, suggest-links, suggest-ai, ai-organize, auto-tag, graph-snapshot,")
            console.print("  graph-history, graph-diff, from-text")
            sys.exit(1)

    except ModuleError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def archive(
    target: str = typer.Argument(..., help="Target: 'decisions', 'current', 'plans'"),
    phase: int = typer.Option(None, "--phase", help="Phase number to archive (backwards compat)"),
    up_to: int = typer.Option(None, "--up-to", help="Archive decisions up to this number (e.g., 25 = #1-#25)"),
    keep_recent: int = typer.Option(None, "--keep-recent", help="Keep only N most recent decisions"),
    older_than: Optional[str] = typer.Option(None, "--older-than", help="Archive decisions older than duration (e.g., 6m, 1y, 180d)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactively select decisions to archive"),
    suggest: bool = typer.Option(False, "--suggest", help="Suggest what to archive (does not archive)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be archived without doing it"),
    module_name: Optional[str] = typer.Option(None, "--module", "-m", help="Module name or path (default: memory-system)"),
):
    """Archive completed documentation (marchive command).

    Examples:
        marchive decisions                              # Keep recent 10 (default)
        marchive decisions --keep-recent 15             # Keep recent 15
        marchive decisions --up-to 25                   # Archive #1-25
        marchive decisions --older-than 6m              # Archive older than 6 months
        marchive decisions --older-than 1y              # Archive older than 1 year
        marchive decisions --interactive                # Interactively select decisions
        marchive decisions --suggest                    # Show suggestions (no archive)
        marchive decisions --phase 5                    # Archive Phase 1-5 (old style)
        marchive current --phase 5                      # Archive Phase 5 current.md
        marchive plans                                  # Move PLAN-*.md to archive
        marchive decisions --dry-run                    # Preview
        marchive decisions --module projects/website    # Archive for specific module
    """
    older_than = opt_str(older_than)
    module_name = opt_str(module_name)

    try:
        from memory_tool.core.archiver import Archiver, ArchiverError
        from memory_tool.utils.config import Config

        resolved_module = resolve_module_name(module_name)
        archiver = Archiver(module_name=resolved_module)

        if target == "decisions":
            if suggest:
                try:
                    result = archiver.suggest_archive()
                    console.print(result['summary'])

                    if result['archive_count'] > 0:
                        console.print("\n[dim]To archive these decisions:[/dim]")
                        console.print(f"[dim]  marchive decisions --older-than 6m[/dim]")
                        console.print(f"[dim]  marchive decisions --interactive[/dim]")
                except ArchiverError as e:
                    console.print(f"[red]ERROR[/red] {e}")
                    sys.exit(1)
                return

            if interactive:
                try:
                    archive_path, num_archived = archiver.archive_decisions_interactive(
                        age_threshold_months=6,
                        dry_run=dry_run
                    )
                    if not dry_run:
                        console.print(f"\n[dim]Backup: decisions.md.bak[/dim]")
                except ArchiverError as e:
                    console.print(f"[red]ERROR[/red] {e}")
                    sys.exit(1)
                return

            options_provided = sum([
                phase is not None,
                up_to is not None,
                keep_recent is not None,
                older_than is not None
            ])

            if options_provided > 1:
                console.print("[red]ERROR[/red] Only one of --phase, --up-to, --keep-recent, or --older-than can be specified")
                sys.exit(1)

            if phase is not None:
                mode = "phase"
                value = phase
            elif up_to is not None:
                mode = "up-to"
                value = up_to
            elif older_than is not None:
                mode = "older-than"
                value = older_than
            else:
                mode = "keep-recent"
                if keep_recent is None:
                    config = Config()
                    value = config.get("modules.archive_keep_recent", 10)
                else:
                    value = keep_recent

            try:
                if mode == "phase":
                    archive_path, num_archived = archiver.archive_decisions(value, dry_run)
                elif mode == "up-to":
                    archive_path, num_archived = archiver.archive_decisions_by_number(value, dry_run)
                elif mode == "older-than":
                    archive_path, num_archived = archiver.archive_decisions_by_date(value, dry_run)
                else:
                    archive_path, num_archived = archiver.archive_decisions_by_count(value, dry_run)

                if dry_run:
                    console.print(f"[cyan]Would archive {num_archived} decisions to:[/cyan]")
                    console.print(f"  {display_path(archive_path)}")
                    console.print(f"\n[dim]Mode: {mode}={value}[/dim]")
                else:
                    console.print(f"[green]OK[/green] Archived {num_archived} decisions")
                    console.print(f"  → {display_path(archive_path)}")
                    console.print(f"\n[dim]Backup: decisions.md.bak[/dim]")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif target == "current":
            if not phase:
                console.print("[red]ERROR[/red] --phase required for current")
                console.print("[dim]Example: marchive current --phase 5[/dim]")
                sys.exit(1)

            try:
                archive_path = archiver.archive_current(phase, dry_run)

                if dry_run:
                    console.print(f"[cyan]Would archive current.md to:[/cyan]")
                    console.print(f"  {display_path(archive_path)}")
                else:
                    console.print(f"[green]OK[/green] Archived current.md")
                    console.print(f"  → {display_path(archive_path)}")
                    console.print(f"\n[dim]Backup: current.md.bak[/dim]")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif target == "plans":
            try:
                archived_files = archiver.archive_plans(dry_run)

                if not archived_files:
                    console.print("[yellow]No PLAN-*.md files found to archive[/yellow]")
                    return

                if dry_run:
                    console.print(f"[cyan]Would move {len(archived_files)} PLAN file(s) to archive/plans/:[/cyan]")
                    for f in archived_files:
                        console.print(f"  - {f.name}")
                else:
                    console.print(f"[green]OK[/green] Moved {len(archived_files)} PLAN file(s) to archive/plans/")
                    for f in archived_files:
                        console.print(f"  - {f.name}")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        else:
            console.print(f"[red]ERROR[/red] Unknown target: {target}")
            console.print("[dim]Valid targets: decisions, current, plans[/dim]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def browse(
    query: str = typer.Argument(None, help="Initial search query"),
    mode: str = typer.Option("search", "--mode", "-m", help="Initial mode: search, timeline, modules, graph"),
):
    """Interactive TUI browser (mbrowse command).

    Launch an enhanced terminal interface with multiple modes:
    - Search: Interactive search with filters
    - Timeline: Date-based timeline explorer
    - Modules: Hierarchical module browser
    - Graph: Module connection graph viewer

    Keybindings:
        Tab: Switch between modes
        /: Focus search (in search mode)
        Enter: Show details
        Esc: Close details
        q: Quit application
        j/k: Navigate (Vim-style)
        n/p: Next/Previous (in timeline)
        r: Refresh
        ?: Help

    Examples:
        mbrowse                       # Launch browser (search mode)
        mbrowse "search query"        # Launch with query
        mbrowse --mode timeline       # Launch in timeline mode
        mbrowse --mode graph          # Launch in graph mode
    """
    try:
        try:
            from memory_tool.tui import run_browser
        except ImportError:
            console.print("[red]ERROR[/red] TUI feature not available")
            console.print("Install with: pip install memory-tool[tui]")
            console.print("Or: pip install textual>=0.47.0")
            sys.exit(1)

        memory_path = get_base_path()

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        valid_modes = ["search", "timeline", "modules", "graph"]
        if mode not in valid_modes:
            console.print(f"[red]ERROR[/red] Invalid mode: {mode}")
            console.print(f"Valid modes: {', '.join(valid_modes)}")
            sys.exit(1)

        run_browser(base_path=Path.cwd(), mode=mode, query=query)

    except KeyboardInterrupt:
        console.print("\n[yellow]Browser closed[/yellow]")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Browser failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
