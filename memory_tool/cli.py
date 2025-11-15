"""CLI interface for Memory Tool."""

import sys
from datetime import timedelta
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.panel import Panel

from memory_tool.core.timeline import (
    Timeline,
    TimelineError,
    FutureTimeError,
    DistantPastWarning,
)
from memory_tool.core.init import (
    MemoryInitializer,
    InitializationError,
    AlreadyInitializedError,
)
from memory_tool.core.search import (
    MemorySearcher,
    SearchError,
)
from memory_tool.core.sort import (
    TimelineSorter,
    SortError,
)
from memory_tool.core.module import (
    ModuleManager,
    ModuleError,
)
from memory_tool.context.builder import (
    ContextBuilder,
    ContextError,
)
from memory_tool.utils.alias import (
    AliasManager,
    AliasError,
)
from memory_tool.utils.config import Config
from memory_tool.llm.client import LLMClient
from memory_tool.summary import (
    TimelineSummarizer,
    ConversationSummarizer,
    ModuleSummarizer,
)

app = typer.Typer(
    name="memory-tool",
    help="Time-Space Integrated Knowledge System",
    add_completion=False,
)
console = Console()


def sanitize_output(text: str) -> str:
    """Remove characters that cause issues with Windows console.

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    # Replace common problematic characters
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


@app.command()
def record(
    message: str = typer.Argument(..., help="Message to record in timeline"),
    date: str = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
    time: str = typer.Option(None, "--time", help="Time (HH:MM)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recording (skip warnings)"),
):
    """Record a message to timeline (m command)."""
    timeline = Timeline()

    try:
        dt, file_path = timeline.record(message, date, time, force=force)

        # Success message
        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%Y-%m-%d")
        rel_path = file_path.relative_to(Path.cwd())

        console.print(f"[green]OK[/green] Recorded at {date_str} {time_str}")
        console.print(f"[dim]-> {rel_path}[/dim]")

        # Auto-update context if enabled
        try:
            config = Config()
            if config.auto_update_enabled:
                console.print("[dim]Auto-updating context...[/dim]")
                builder = ContextBuilder()
                context_path = builder.write_context()
                rel_context = context_path.relative_to(Path.cwd())
                console.print(f"[dim]-> {rel_context} updated[/dim]")
        except Exception as e:
            # Don't fail the record if auto-update fails
            console.print(f"[yellow]Warning:[/yellow] Auto-update failed: {e}")

        # Check file sizes and show warnings
        try:
            from memory_tool.core.warnings import FileSizeWarning

            warning_system = FileSizeWarning()
            warnings = warning_system.check_sizes()

            if warnings:
                console.print()  # Blank line
                console.print(warning_system.format_warning(warnings))
        except Exception:
            # Don't fail the record if warning check fails
            pass

    except FutureTimeError as e:
        console.print(f"[red]ERROR[/red] {e}", style="bold")
        sys.exit(1)

    except DistantPastWarning as e:
        console.print(f"[yellow]WARNING[/yellow] {e}")
        console.print("[dim]Use --force to record anyway[/dim]")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except TimelineError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to initialize .memory/ structure"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialize"),
    kb: str = typer.Option(None, "--kb", help="Path to knowledge base"),
):
    """Initialize .memory/ structure (minit command)."""
    target_path = Path(path).resolve()

    if not target_path.exists():
        console.print(f"[red]ERROR[/red] Path does not exist: {target_path}")
        sys.exit(1)

    if not target_path.is_dir():
        console.print(f"[red]ERROR[/red] Path is not a directory: {target_path}")
        sys.exit(1)

    initializer = MemoryInitializer(target_path)

    try:
        created = initializer.initialize(force=force, kb_path=kb)

        # Success message
        console.print(f"[green]OK[/green] Initialized .memory/ at: {target_path}")
        console.print(f"[dim]Created {len(created['directories'])} directories, {len(created['files'])} files[/dim]")

        if kb:
            console.print(f"[dim]Knowledge base: {kb}[/dim]")

        # Claude Code integration info
        template_path = target_path / ".memory" / "templates" / "CLAUDE.md.template"
        console.print(f"\n[cyan]Claude Code Integration:[/cyan]")
        console.print(f"[dim]Template: {template_path}[/dim]")
        console.print(f"[dim]Copy sections to your CLAUDE.md to integrate with Claude Code[/dim]")

    except AlreadyInitializedError as e:
        console.print(f"[yellow]WARNING[/yellow] {e}")
        console.print("[dim]Use --force to reinitialize[/dim]")
        sys.exit(1)

    except InitializationError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (regex pattern or semantic)"),
    with_kb: bool = typer.Option(False, "--with-kb", help="Include personal KB"),
    all: bool = typer.Option(False, "--all", help="Search all projects"),
    case_sensitive: bool = typer.Option(False, "--case", "-c", help="Case sensitive search"),
    no_context: bool = typer.Option(False, "--no-context", help="Hide context lines"),
    max_results: int = typer.Option(None, "--max", "-n", help="Maximum results"),
    from_date: str = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: str = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    semantic: bool = typer.Option(False, "--semantic", "-s", help="Semantic search using embeddings"),
    threshold: float = typer.Option(0.3, "--threshold", "-t", help="Similarity threshold (0-1, semantic only)"),
    no_index: bool = typer.Option(False, "--no-index", help="Force file-based search (skip SQLite index)"),
    # New ranking options
    rank: str = typer.Option(None, "--rank", help="Ranking algorithm: bm25 (default: none)"),
    boost_recent: bool = typer.Option(False, "--boost-recent", help="Boost recent results"),
    decay_days: int = typer.Option(30, "--decay-days", help="Date decay days (for --boost-recent)"),
    # New filter options
    date: str = typer.Option(None, "--date", help="Date expression: today, yesterday, this-week, last-N-days, YYYY-MM-DD"),
    file_type: str = typer.Option(None, "--type", help="File type: timeline, modules, decisions, plans, archive"),
    tag: List[str] = typer.Option(None, "--tag", help="Filter by tags (can use multiple times)"),
    # New formatting options
    show_score: bool = typer.Option(False, "--show-score", help="Show relevance scores"),
    summary: bool = typer.Option(False, "--summary", help="Show summary statistics"),
    # Phase 2 & 3 options
    hybrid: bool = typer.Option(False, "--hybrid", help="Hybrid search (text + semantic)"),
    text_weight: float = typer.Option(0.7, "--text-weight", help="Text weight for hybrid search (default: 0.7)"),
    semantic_weight: float = typer.Option(0.3, "--semantic-weight", help="Semantic weight for hybrid search (default: 0.3)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable result caching"),
    cache_ttl: int = typer.Option(3600, "--cache-ttl", help="Cache TTL in seconds (default: 3600 / 1 hour)"),
):
    """Search timeline and modules (ms command).

    Examples:
        ms "bug fix" --rank bm25 --boost-recent
        ms "feature" --date this-week --type timeline
        ms "decision" --show-score --summary
        ms "implementation" --hybrid --text-weight 0.5 --semantic-weight 0.5
        ms "query" --no-cache
    """
    # Initialize cache if enabled
    search_cache = None
    cache_key_params = {
        "with_kb": with_kb,
        "all": all,
        "case_sensitive": case_sensitive,
        "max_results": max_results,
        "from_date": from_date,
        "to_date": to_date,
        "rank": rank,
        "boost_recent": boost_recent,
        "date": date,
        "file_type": file_type,
        "tag": tuple(tag) if tag else None,
        "hybrid": hybrid,
        "text_weight": text_weight if hybrid else None,
        "semantic_weight": semantic_weight if hybrid else None,
    }

    if not no_cache:
        from memory_tool.search import SearchCache
        from pathlib import Path
        cache_dir = Path.home() / ".memory" / ".cache" / "search"
        search_cache = SearchCache(cache_dir, ttl_seconds=cache_ttl)

        # Try to get cached results
        cached_results = search_cache.get(query, **cache_key_params)
        if cached_results:
            console.print("[dim]Using cached results...[/dim]\n")
            # Display cached results using formatter
            if show_score or summary or not no_context:
                from memory_tool.search import ResultFormatter
                formatter = ResultFormatter(Path.cwd())
                formatter.print_results(
                    cached_results,
                    query=query,
                    show_score=show_score,
                    show_context=not no_context,
                    context_lines=1,
                    highlight=True,
                    show_summary=summary,
                )
            else:
                # Simple display
                for i, result in enumerate(cached_results, 1):
                    console.print(f"{i}. {result.file_path}:{result.line_number}")
            return

    # Hybrid search mode: combine text + semantic
    if hybrid:
        try:
            from memory_tool.core.vector_search import VectorSearcher, VectorSearchNotAvailableError
            from memory_tool.search import HybridSearcher
            from memory_tool.core.search import SearchResult

            # Perform text search
            searcher = MemorySearcher()
            scope = "all" if all else "local"

            from datetime import datetime
            parsed_from = None
            parsed_to = None

            try:
                if from_date:
                    parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
                if to_date:
                    parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()
            except ValueError as e:
                console.print(f"[red]ERROR[/red] Invalid date format: {e}")
                sys.exit(1)

            # Text search
            text_results_dict = searcher.search(
                query,
                scope=scope,
                with_kb=with_kb,
                case_sensitive=case_sensitive,
                context_lines=1,
                max_results=max_results or 50,
                from_date=parsed_from,
                to_date=parsed_to,
                use_index=not no_index,
            )

            text_results = []
            for source_results in text_results_dict.values():
                text_results.extend(source_results)

            # Extract dates
            for result in text_results:
                date_from_path = searcher._extract_date_from_path(result.file_path)
                if date_from_path:
                    result.date = datetime.combine(date_from_path, datetime.min.time())

            # Semantic search
            try:
                vector_searcher = VectorSearcher()
                semantic_results_list = vector_searcher.semantic_search(
                    query,
                    top_k=max_results or 50,
                    threshold=threshold
                )

                # Convert to SearchResult format
                semantic_results = []
                for r in semantic_results_list:
                    semantic_results.append(SearchResult(
                        file_path=Path(r['file']),
                        line_number=r['line'],
                        line_content=r['content'],
                        match_context=r['content'],
                        score=r['similarity'],
                        date=datetime.fromisoformat(r['date']) if r.get('date') else None,
                    ))

                # Combine with HybridSearcher
                hybrid_searcher = HybridSearcher()
                all_results = hybrid_searcher.combine_results(
                    text_results,
                    semantic_results,
                    text_weight,
                    semantic_weight,
                )

                console.print(f"[cyan]Hybrid Search Results[/cyan] (text: {text_weight:.1f}, semantic: {semantic_weight:.1f})\n")

                # Apply filters and ranking
                if date or file_type or tag:
                    from memory_tool.search import FilterChain
                    filter_chain = FilterChain(searcher.base_path)
                    all_results = filter_chain.apply_filters(
                        all_results,
                        date_expr=date,
                        file_type=file_type,
                        tags=tag if tag else None,
                    )

                if rank or boost_recent:
                    from memory_tool.search import SearchRanker
                    use_bm25 = (rank == "bm25")
                    ranker = SearchRanker(
                        use_bm25=use_bm25,
                        use_date_weight=boost_recent,
                        date_decay_days=decay_days,
                    )
                    all_results = ranker.rank(query, all_results)

                # Cache results
                if search_cache:
                    search_cache.set(query, all_results, **cache_key_params)

                # Display results
                if all_results:
                    if show_score or summary or not no_context:
                        from memory_tool.search import ResultFormatter
                        formatter = ResultFormatter(searcher.base_path)
                        formatter.print_results(
                            all_results,
                            query=query,
                            show_score=show_score,
                            show_context=not no_context,
                            context_lines=1,
                            highlight=True,
                            show_summary=summary,
                        )
                    else:
                        for i, result in enumerate(all_results[:max_results] if max_results else all_results, 1):
                            console.print(f"{i}. {result.file_path}:{result.line_number}")
                else:
                    console.print("[yellow]No results found[/yellow]")

                return

            except VectorSearchNotAvailableError as e:
                console.print(f"[red]ERROR[/red] {e}")
                console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
                sys.exit(1)

        except ImportError:
            console.print("[red]ERROR[/red] Vector search not available for hybrid mode")
            console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
            sys.exit(1)

    # Use vector search if --semantic flag is set (semantic only)
    if semantic:
        try:
            from memory_tool.core.vector_search import VectorSearcher, VectorSearchNotAvailableError

            try:
                vector_searcher = VectorSearcher()
                results_list = vector_searcher.semantic_search(
                    query,
                    top_k=max_results or 10,
                    threshold=threshold
                )

                # Format results
                if not results_list:
                    console.print("[yellow]No results found[/yellow]")
                    return

                console.print(f"[cyan]Semantic Search Results[/cyan] (similarity >= {threshold})\n")
                for i, result in enumerate(results_list, 1):
                    similarity_color = "green" if result['similarity'] > 0.7 else "yellow" if result['similarity'] > 0.5 else "dim"
                    sanitized_content = sanitize_output(result['content'])
                    console.print(f"[{similarity_color}]{i}. [{result['similarity']:.2f}][/{similarity_color}] {result['file']}:{result['line']}")
                    console.print(f"   [dim]{result['date']}[/dim] | {sanitized_content}")
                    console.print()

                return

            except VectorSearchNotAvailableError as e:
                console.print(f"[red]ERROR[/red] {e}")
                console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
                sys.exit(1)

        except ImportError:
            console.print("[red]ERROR[/red] Vector search not available")
            console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
            sys.exit(1)

    # Regular search
    searcher = MemorySearcher()

    # Determine scope
    if all:
        scope = "all"
    else:
        scope = "local"

    # Parse dates (legacy --from/--to support)
    from datetime import datetime
    parsed_from = None
    parsed_to = None

    try:
        if from_date:
            parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
        if to_date:
            parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()

        # Validate date range
        if parsed_from and parsed_to and parsed_from > parsed_to:
            console.print("[red]ERROR[/red] --from date must be before --to date")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] Invalid date format: {e}")
        console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
        sys.exit(1)

    try:
        results_dict = searcher.search(
            query,
            scope=scope,
            with_kb=with_kb,
            case_sensitive=case_sensitive,
            context_lines=1 if not no_context else 0,
            max_results=max_results,
            from_date=parsed_from,
            to_date=parsed_to,
            use_index=not no_index,
        )

        # Convert dict results to flat list of SearchResults
        from memory_tool.core.search import SearchResult
        all_results = []
        for source_path, source_results in results_dict.items():
            all_results.extend(source_results)

        # Extract dates for results from file paths
        for result in all_results:
            date_from_path = searcher._extract_date_from_path(result.file_path)
            if date_from_path:
                result.date = datetime.combine(date_from_path, datetime.min.time())

        # Apply enhanced filters
        if date or file_type or tag:
            from memory_tool.search import FilterChain
            filter_chain = FilterChain(searcher.base_path)
            all_results = filter_chain.apply_filters(
                all_results,
                date_expr=date,
                file_type=file_type,
                tags=tag if tag else None,
            )

        # Apply ranking
        if rank or boost_recent:
            from memory_tool.search import SearchRanker

            use_bm25 = (rank == "bm25")
            ranker = SearchRanker(
                use_bm25=use_bm25,
                use_date_weight=boost_recent,
                date_decay_days=decay_days,
            )

            all_results = ranker.rank(query, all_results)

        # Limit results if needed
        if max_results and len(all_results) > max_results:
            all_results = all_results[:max_results]

        # Cache results
        if search_cache:
            search_cache.set(query, all_results, **cache_key_params)

        # Format and display
        if show_score or summary or not no_context:
            # Use enhanced formatter
            from memory_tool.search import ResultFormatter
            formatter = ResultFormatter(searcher.base_path)

            formatter.print_results(
                all_results,
                query=query,
                show_score=show_score,
                show_context=not no_context,
                context_lines=1,
                highlight=True,
                show_summary=summary,
            )
        else:
            # Use simple formatter
            formatted = searcher.format_results(
                {str(searcher.memory_path): all_results},
                show_context=not no_context
            )
            console.print(formatted)

    except SearchError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def context(
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: .claude/memory-context.md)",
    ),
):
    """Build context for Claude Code (mcontext command)."""
    builder = ContextBuilder()

    # Parse output path
    output_path = Path(output) if output else None

    try:
        result_path = builder.write_context(output_path)

        # Success message
        try:
            rel_path = result_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = result_path
        console.print(f"[green]OK[/green] Context built successfully")
        console.print(f"[dim]-> {rel_path}[/dim]")

        # Show what was included
        config = builder.load_config()
        recent_days = config.get("context", {}).get("recent_days", 3)
        timeline_count = len(builder.get_recent_timeline_paths(recent_days))
        module_count = len(builder.get_module_statuses())

        console.print(f"[dim]Included: {timeline_count} timeline(s), {module_count} module(s)[/dim]")

    except ContextError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def today():
    """Show today's timeline (mtoday command)."""
    timeline = Timeline()

    try:
        file_path, content = timeline.get_today()

        if file_path is None:
            console.print("[yellow]![/yellow] No timeline entries for today yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        # Display today's timeline
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        console.print(f"[cyan]{today_str} Timeline:[/cyan]\n")
        console.print(sanitize_output(content))
        console.print(f"\n[dim]File: {file_path}[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read today's timeline: {e}")
        sys.exit(1)


@app.command()
def week():
    """Show this week's timeline (mweek command)."""
    timeline = Timeline()

    try:
        week_files = timeline.get_week()

        if not week_files:
            console.print("[yellow]![/yellow] No timeline entries for this week yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        # Display week's timeline
        from datetime import datetime
        today = datetime.now()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)

        console.print(f"[cyan]Week of {monday.strftime('%Y-%m-%d')} Timeline:[/cyan]\n")

        for file_path, content in week_files:
            # Extract date from path (YYYY-MM/DD.md)
            year_month = file_path.parent.name
            day = file_path.stem
            date_str = f"{year_month}-{day}"

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")  # Blank line between days

        total_days = len(week_files)
        console.print(f"[dim]{total_days} day(s) with entries this week[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read week's timeline: {e}")
        sys.exit(1)


@app.command()
def status():
    """Show statistics (mstatus command)."""
    base_path = Path.cwd()
    memory_path = base_path / ".memory"

    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found in current directory")
        console.print("[dim]Run 'minit' to initialize[/dim]")
        sys.exit(1)

    try:
        # Count timeline files
        timeline_path = memory_path / "timeline"
        timeline_files = list(timeline_path.rglob("*.md")) if timeline_path.exists() else []
        timeline_count = len(timeline_files)

        # Count entries in timeline files
        total_entries = 0
        latest_date = None
        for tf in timeline_files:
            content = tf.read_text(encoding="utf-8")
            lines = content.splitlines()
            # Count lines starting with "-" (entries)
            entries = [line for line in lines if line.strip().startswith("-")]
            total_entries += len(entries)

            # Track latest date
            year_month = tf.parent.name
            day = tf.stem
            try:
                from datetime import datetime
                file_date = datetime.strptime(f"{year_month}-{day}", "%Y-%m-%d")
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
            except:
                pass

        # Count modules
        modules_path = memory_path / "modules"
        module_dirs = []
        if modules_path.exists():
            module_dirs = [d for d in modules_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        modules_count = len(module_dirs)

        # Count concepts
        concepts_path = memory_path / "concepts"
        concept_files = list(concepts_path.glob("*.md")) if concepts_path.exists() else []
        concepts_count = len(concept_files)

        # Calculate .memory size
        total_size = 0
        for item in memory_path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size

        size_mb = total_size / (1024 * 1024)

        # Display statistics
        console.print("[cyan]Memory Tool Statistics:[/cyan]\n")

        console.print(f"[bold]Timeline:[/bold]")
        console.print(f"  Days recorded: {timeline_count}")
        console.print(f"  Total entries: {total_entries}")
        if latest_date:
            console.print(f"  Latest: {latest_date.strftime('%Y-%m-%d')}")
        console.print()

        console.print(f"[bold]Organization:[/bold]")
        console.print(f"  Modules: {modules_count}")
        console.print(f"  Concepts: {concepts_count}")
        console.print()

        console.print(f"[bold]Storage:[/bold]")
        console.print(f"  Size: {size_mb:.2f} MB")
        console.print(f"  Location: {memory_path}")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to collect statistics: {e}")
        sys.exit(1)


@app.command()
def alias(
    action: str = typer.Argument(..., help="Action: install, uninstall, list"),
    name: str = typer.Argument(None, help="Alias name (optional, default: all)"),
    directory: str = typer.Option(None, "--dir", "-d", help="Installation directory (for batch files)"),
    powershell: bool = typer.Option(False, "--powershell", "--ps", help="Use PowerShell profile (works in all terminals)"),
):
    """Manage command aliases (malias command)."""
    manager = AliasManager()

    # Parse directory
    install_dir = Path(directory) if directory else None

    try:
        if action == "install":
            if powershell:
                # Install to PowerShell profile
                if name:
                    # Install single alias
                    profile_path, was_added = manager.install_powershell_alias(name)
                    if was_added:
                        console.print(f"[green]OK[/green] Installed alias to PowerShell profile: {name}")
                    else:
                        console.print(f"[yellow]![/yellow] Alias already exists: {name}")
                    console.print(f"[dim]-> {profile_path}[/dim]")
                else:
                    # Install all aliases
                    installed = manager.install_all_powershell()
                    added_count = sum(1 for was_added in installed.values() if was_added)
                    console.print(f"[green]OK[/green] Installed {added_count} aliases to PowerShell profile")

                    profile_path = manager.get_powershell_profile_path()
                    console.print(f"[dim]Profile: {profile_path}[/dim]\n")

                    for alias_name, was_added in installed.items():
                        command, description = manager.ALIASES[alias_name]
                        if was_added:
                            console.print(f"[green]  + {alias_name:10}[/green] -> {command:10} ({description})")
                        else:
                            console.print(f"[dim]  = {alias_name:10} -> {command:10} (already exists)[/dim]")

                # Show reload instructions
                console.print("\n[cyan]To use aliases, reload your PowerShell profile:[/cyan]")
                console.print("[dim]  . $PROFILE[/dim]")
                console.print("[dim]Or restart your terminal[/dim]")
            else:
                # Install batch files (original behavior)
                if name:
                    # Install single alias
                    batch_file = manager.install_alias(name, install_dir)
                    console.print(f"[green]OK[/green] Installed alias: {name}")
                    console.print(f"[dim]-> {batch_file}[/dim]")
                else:
                    # Install all aliases
                    installed = manager.install_all(install_dir)
                    console.print(f"[green]OK[/green] Installed {len(installed)} aliases")
                    for alias_name, batch_file in installed.items():
                        console.print(f"[dim]  {alias_name} -> {batch_file}[/dim]")

                # Show PATH instructions
                target_dir = install_dir or manager.get_default_install_dir()
                instructions = manager.get_path_instructions(target_dir)
                console.print(instructions)

        elif action == "uninstall":
            if powershell:
                # Uninstall from PowerShell profile
                if name:
                    # Uninstall single alias
                    profile_path, was_removed = manager.uninstall_powershell_alias(name)
                    if was_removed:
                        console.print(f"[green]OK[/green] Uninstalled alias from PowerShell profile: {name}")
                        if profile_path:
                            console.print(f"[dim]-> {profile_path}[/dim]")
                    else:
                        console.print(f"[yellow]![/yellow] Alias not found: {name}")
                else:
                    # Uninstall all aliases
                    removed = manager.uninstall_all_powershell()
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled {len(removed)} aliases from PowerShell profile")
                        for alias_name in removed:
                            console.print(f"[dim]  {alias_name}[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found to uninstall")

                # Show reload instructions
                console.print("\n[cyan]To apply changes, reload your PowerShell profile:[/cyan]")
                console.print("[dim]  . $PROFILE[/dim]")
                console.print("[dim]Or restart your terminal[/dim]")
            else:
                # Uninstall batch files (original behavior)
                if name:
                    # Uninstall single alias
                    removed = manager.uninstall_alias(name, install_dir)
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled alias: {name}")
                    else:
                        console.print(f"[yellow]![/yellow] Alias not found: {name}")
                else:
                    # Uninstall all aliases
                    removed = manager.uninstall_all(install_dir)
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled {len(removed)} aliases")
                        for alias_name in removed:
                            console.print(f"[dim]  {alias_name}[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found to uninstall")

        elif action == "list":
            if powershell:
                # List PowerShell profile aliases
                ps_status_map = manager.list_powershell_installed()
                ps_profile = manager.get_powershell_profile_path()

                if ps_profile:
                    console.print(f"[cyan]PowerShell Profile:[/cyan] {ps_profile}\n")

                    for alias_name, installed in ps_status_map.items():
                        command, description = manager.ALIASES[alias_name]
                        status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                        console.print(f"  {status_icon} {alias_name:10} -> {command:10} ({description})")

                    console.print("")
                    if any(ps_status_map.values()):
                        console.print("[green]OK[/green] Aliases are configured in PowerShell profile")
                        console.print("[dim]Works in: PowerShell, VSCode, Windows Terminal, etc.[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found in PowerShell profile")
                        console.print("[dim]Run 'malias install --powershell' to install[/dim]")
                else:
                    console.print("[red]ERROR[/red] PowerShell not available")
            else:
                # List batch file aliases (original behavior) and PowerShell status
                # Show batch files
                status_map = manager.list_installed(install_dir)
                target_dir = install_dir or manager.get_default_install_dir()

                console.print(f"[cyan]Batch Files:[/cyan] {target_dir}\n")

                for alias_name, installed in status_map.items():
                    command, description = manager.ALIASES[alias_name]
                    status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                    console.print(f"  {status_icon} {alias_name:10} -> {command:10} ({description})")

                console.print("")
                in_path = manager.is_in_path(target_dir)
                if in_path:
                    console.print("[green]OK[/green] Directory is in PATH")
                else:
                    console.print("[yellow]![/yellow] Directory is NOT in PATH (aliases won't work)")
                    console.print("[dim]Run 'malias install' to see PATH setup instructions[/dim]")

                # Also show PowerShell profile status
                ps_profile = manager.get_powershell_profile_path()
                if ps_profile:
                    ps_status_map = manager.list_powershell_installed()
                    console.print(f"\n[cyan]PowerShell Profile:[/cyan] {ps_profile}")

                    ps_installed_count = sum(1 for v in ps_status_map.values() if v)
                    if ps_installed_count > 0:
                        console.print(f"[green]OK[/green] {ps_installed_count} aliases configured in PowerShell profile")
                    else:
                        console.print("[dim]No PowerShell aliases (use --powershell to install)[/dim]")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("Valid actions: install, uninstall, list")
            sys.exit(1)

    except AliasError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def sort(
    date_or_all: str = typer.Argument("today", help="Date (YYYY-MM-DD), 'today', or 'all'"),
    no_backup: bool = typer.Option(False, "--no-backup", help="Skip backup creation"),
):
    """Sort timeline entries by time (msort command)."""
    sorter = TimelineSorter()

    # Check if initialized
    if not sorter.is_initialized():
        console.print(f"[red]ERROR[/red] Timeline not found at {sorter.timeline_path}")
        console.print("[dim]Run 'minit' to initialize[/dim]")
        sys.exit(1)

    try:
        # Parse date argument
        from datetime import datetime, date

        if date_or_all.lower() == "all":
            # Sort all timeline files
            console.print("[cyan]Sorting all timeline files...[/cyan]")
            results = sorter.sort_all(create_backup=not no_backup)

            if not results:
                console.print("[yellow]No timeline files found[/yellow]")
                sys.exit(0)

            # Display results
            total_files = len(results)
            total_entries = sum(r[1] for r in results)
            total_sorted = sum(r[2] for r in results)

            console.print(f"\n[green]OK[/green] Sorted {total_files} file(s)")
            console.print(f"  Total entries: {total_entries}")
            console.print(f"  Sorted entries: {total_sorted}")
            console.print(f"  Unsorted entries: {total_entries - total_sorted}")

            if not no_backup:
                console.print(f"\n[dim]Backups created with .bak extension[/dim]")

        elif date_or_all.lower() == "today":
            # Sort today's file
            today = date.today()
            year_month = today.strftime("%Y-%m")
            day = today.strftime("%d")

            file_path = sorter.timeline_path / year_month / f"{day}.md"

            if not file_path.exists():
                console.print(f"[yellow]No timeline file for today ({today.strftime('%Y-%m-%d')})[/yellow]")
                sys.exit(0)

            console.print(f"[cyan]Sorting {today.strftime('%Y-%m-%d')}...[/cyan]")
            total, sorted_count = sorter.sort_file(file_path, create_backup=not no_backup)

            console.print(f"\n[green]OK[/green] Sorted {file_path.name}")
            console.print(f"  Total entries: {total}")
            console.print(f"  Sorted entries: {sorted_count}")
            console.print(f"  Unsorted entries: {total - sorted_count}")

            if not no_backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                console.print(f"\n[dim]Backup: {backup_path.name}[/dim]")

        else:
            # Parse specific date
            try:
                target_date = datetime.strptime(date_or_all, "%Y-%m-%d").date()
            except ValueError:
                console.print(f"[red]ERROR[/red] Invalid date format: {date_or_all}")
                console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
                sys.exit(1)

            year_month = target_date.strftime("%Y-%m")
            day = target_date.strftime("%d")

            file_path = sorter.timeline_path / year_month / f"{day}.md"

            if not file_path.exists():
                console.print(f"[yellow]No timeline file for {date_or_all}[/yellow]")
                sys.exit(0)

            console.print(f"[cyan]Sorting {date_or_all}...[/cyan]")
            total, sorted_count = sorter.sort_file(file_path, create_backup=not no_backup)

            console.print(f"\n[green]OK[/green] Sorted {file_path.name}")
            console.print(f"  Total entries: {total}")
            console.print(f"  Sorted entries: {sorted_count}")
            console.print(f"  Unsorted entries: {total - sorted_count}")

            if not no_backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                console.print(f"\n[dim]Backup: {backup_path.name}[/dim]")

    except SortError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def module(
    action: str = typer.Argument(..., help="Action: create, list, archive, unarchive"),
    name: str = typer.Argument(None, help="Module name"),
    description: str = typer.Option("", "--desc", "-d", help="Module description"),
    reason: str = typer.Option("", "--reason", "-r", help="Reason for archiving"),
    tags: str = typer.Option("", "--tags", "-t", help="Module tags (comma-separated)"),
    archived: bool = typer.Option(False, "--archived", "-a", help="Include archived modules in list"),
):
    """Manage modules."""
    manager = ModuleManager()

    try:
        if action.lower() == "create":
            # Create new module
            if not name:
                console.print("[red]ERROR[/red] Module name is required for create")
                console.print("[dim]Usage: module create <name> [--desc \"description\"][/dim]")
                sys.exit(1)

            # Parse tags
            tag_list = [t.strip() for t in tags.split(",")] if tags else []

            console.print(f"[cyan]Creating module '{name}'...[/cyan]")
            module_path = manager.create(name, description, tag_list)

            # Success
            rel_path = module_path.relative_to(Path.cwd())
            console.print(f"\n[green]OK[/green] Module created: {name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")
            console.print(f"\n[dim]Files created:[/dim]")
            console.print(f"  - module.md      (module definition)")
            console.print(f"  - current.md     (current status)")
            console.print(f"  - decisions.md   (decisions)")
            console.print(f"  - dependencies.md (dependencies)")
            console.print(f"  - interface.md   (interface/API)")

        elif action.lower() == "list":
            # List modules
            modules = manager.list_modules(include_archived=archived)

            # Display active modules
            active = modules.get("active", [])
            console.print(f"[cyan]Active Modules:[/cyan] {len(active)}\n")

            if active:
                for mod_name in active:
                    console.print(f"  - {mod_name}")
            else:
                console.print("  [dim]No active modules[/dim]")

            # Display archived modules
            if archived and "archived" in modules:
                arch = modules["archived"]
                console.print(f"\n[cyan]Archived Modules:[/cyan] {len(arch)}\n")

                if arch:
                    for mod_name in arch:
                        console.print(f"  - {mod_name}")
                else:
                    console.print("  [dim]No archived modules[/dim]")

        elif action.lower() == "archive":
            # Archive module
            if not name:
                console.print("[red]ERROR[/red] Module name is required for archive")
                console.print("[dim]Usage: module archive <name> [--reason \"reason\"][/dim]")
                sys.exit(1)

            console.print(f"[cyan]Archiving module '{name}'...[/cyan]")
            archive_path = manager.archive(name, reason)

            # Success
            rel_path = archive_path.relative_to(Path.cwd())
            console.print(f"\n[green]OK[/green] Module archived: {name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")

            if reason:
                console.print(f"[dim]Reason: {reason}[/dim]")

        elif action.lower() == "unarchive":
            # Restore module from archive
            if not name:
                console.print("[red]ERROR[/red] Module name is required for unarchive")
                console.print("[dim]Usage: module unarchive <name>[/dim]")
                sys.exit(1)

            console.print(f"[cyan]Restoring module '{name}' from archive...[/cyan]")
            module_path = manager.unarchive(name)

            # Success
            rel_path = module_path.relative_to(Path.cwd())
            console.print(f"\n[green]OK[/green] Module restored: {name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("Valid actions: create, list, archive, unarchive")
            sys.exit(1)

    except ModuleError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def summary(
    scope: str = typer.Argument("today", help="Scope: 'today', 'week', date (YYYY-MM-DD), or date range (YYYY-MM-DD:YYYY-MM-DD)"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path (optional)"),
    module_name: str = typer.Option(None, "--module", "-m", help="Summarize specific module"),
    lang: str = typer.Option(None, "--lang", "-l", help="Output language: 'ko' (Korean), 'en' (English), 'auto' (detect)"),
):
    """Summarize timeline or module using LLM (msummary command)."""
    # Check if LLM is available
    if not LLMClient.check_availability():
        console.print("[red]ERROR[/red] LLM not configured")
        console.print("[dim]Set ANTHROPIC_API_KEY environment variable or add 'llm.api_key' to config.yaml[/dim]")
        sys.exit(1)

    try:
        llm_client = LLMClient()

        # Module summarization
        if module_name:
            console.print(f"[cyan]Summarizing module '{module_name}'...[/cyan]")

            summarizer = ModuleSummarizer(llm_client)
            module_path = Path.cwd() / ".memory" / "modules" / module_name

            summary_text = summarizer.summarize_module(module_path)

            # Display summary
            console.print("\n" + "="*80)
            console.print(summary_text)
            console.print("="*80)

            # Save to file if requested
            if output:
                output_path = Path(output)
                output_path.write_text(summary_text, encoding="utf-8")
                console.print(f"\n[green]OK[/green] Summary saved to: {output}")

            return

        # Timeline summarization
        from datetime import datetime

        summarizer = TimelineSummarizer(llm_client)

        # Parse scope
        if scope.lower() == "today":
            console.print("[cyan]Summarizing today's timeline...[/cyan]")
            summary_text = summarizer.summarize_today(output_language=lang)

        elif scope.lower() == "week":
            console.print("[cyan]Summarizing this week's timeline...[/cyan]")
            summary_text = summarizer.summarize_week(output_language=lang)

        elif ":" in scope:
            # Date range: YYYY-MM-DD:YYYY-MM-DD
            try:
                start_str, end_str = scope.split(":")
                start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()

                console.print(f"[cyan]Summarizing timeline from {start_date} to {end_date}...[/cyan]")
                summary_text = summarizer.summarize_range(start_date, end_date, output_language=lang)

            except ValueError as e:
                console.print(f"[red]ERROR[/red] Invalid date range format: {scope}")
                console.print("[dim]Use: YYYY-MM-DD:YYYY-MM-DD (e.g., 2025-11-01:2025-11-14)[/dim]")
                sys.exit(1)

        else:
            # Specific date: YYYY-MM-DD
            try:
                target_date = datetime.strptime(scope, "%Y-%m-%d").date()
                console.print(f"[cyan]Summarizing timeline for {target_date}...[/cyan]")
                summary_text = summarizer.summarize_date(target_date, output_language=lang)

            except ValueError:
                console.print(f"[red]ERROR[/red] Invalid date format: {scope}")
                console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
                sys.exit(1)

        # Display summary
        console.print("\n" + "="*80)
        console.print(summary_text)
        console.print("="*80)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.write_text(summary_text, encoding="utf-8")
            console.print(f"\n[green]OK[/green] Summary saved to: {output}")

    except FileNotFoundError as e:
        console.print(f"[yellow]![/yellow] {e}")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def index(
    check: bool = typer.Option(False, "--check", help="Check index status"),
    stats: bool = typer.Option(False, "--stats", help="Show index statistics"),
    force: bool = typer.Option(False, "--force", "-f", help="Force full reindex"),
    optimize: bool = typer.Option(False, "--optimize", help="Optimize index for better performance"),
    vacuum: bool = typer.Option(False, "--vacuum", help="Vacuum database to reclaim space"),
):
    """Manage SQLite search index."""
    try:
        from memory_tool.db import IndexManager

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        # Check SQLite availability
        if not IndexManager.available():
            console.print("[red]ERROR[/red] SQLite with FTS5 not available")
            console.print("Indexing requires SQLite 3.9.0+ with FTS5 support")
            sys.exit(1)

        indexer = IndexManager(memory_path)

        # Check mode
        if check:
            is_fresh = indexer.is_index_fresh()
            if is_fresh:
                console.print("[green]Index is up to date[/green]")
            else:
                console.print("[yellow]Index is stale or missing[/yellow]")
                console.print("Run 'mindex' to rebuild")
            return

        # Stats mode
        if stats:
            stats_data = indexer.get_stats()
            if stats_data["status"] == "not_created":
                console.print("[yellow]Index not created yet[/yellow]")
                console.print("Run 'mindex' to create index")
            else:
                console.print(f"[green]Index Status: OK[/green]")
                console.print(f"Total entries: {stats_data['total_entries']}")
                console.print(f"Size: {stats_data['size_mb']} MB")
                console.print("\nEntries by type:")
                for entry_type, count in stats_data['by_type'].items():
                    console.print(f"  {entry_type}: {count}")
            return

        # Optimize mode
        if optimize or vacuum:
            from memory_tool.search import IndexOptimizer

            db_path = memory_path / ".index" / "search.db"
            if not db_path.exists():
                console.print("[red]ERROR[/red] Index database not found")
                console.print("Run 'mindex' to create index first")
                sys.exit(1)

            optimizer = IndexOptimizer(db_path)

            if optimize and vacuum:
                # Full optimization
                console.print("Running full optimization...")
                result = optimizer.full_optimize()

                if result.get("overall_success"):
                    console.print("[green]Optimization complete![/green]")

                    # Show FTS5 results
                    fts_result = result.get("fts5_optimize", {})
                    if fts_result.get("success"):
                        console.print(f"  FTS5: {fts_result.get('entries_indexed', 0)} entries optimized")

                    # Show vacuum results
                    vacuum_result = result.get("vacuum", {})
                    if vacuum_result.get("success"):
                        reduced_mb = vacuum_result.get("size_reduced_mb", 0)
                        percent = vacuum_result.get("percent_reduced", 0)
                        console.print(f"  Vacuum: {reduced_mb:.2f} MB reclaimed ({percent:.1f}%)")
                else:
                    console.print("[yellow]Optimization completed with errors[/yellow]")
                    for key, res in result.items():
                        if res.get("error"):
                            console.print(f"  {key}: {res['error']}")

            elif optimize:
                # FTS5 optimize only
                console.print("Optimizing FTS5 index...")
                result = optimizer.optimize_fts5()

                if result.get("success"):
                    console.print(f"[green]OK[/green] {result.get('message')}")
                    console.print(f"  Entries: {result.get('entries_indexed', 0)}")
                else:
                    console.print(f"[red]ERROR[/red] {result.get('error')}")
                    sys.exit(1)

            elif vacuum:
                # Vacuum only
                console.print("Vacuuming database...")
                result = optimizer.vacuum_database()

                if result.get("success"):
                    reduced_mb = result.get("size_reduced_mb", 0)
                    percent = result.get("percent_reduced", 0)
                    console.print(f"[green]OK[/green] {reduced_mb:.2f} MB reclaimed ({percent:.1f}%)")
                    console.print(f"  Before: {result.get('size_before_mb', 0):.2f} MB")
                    console.print(f"  After: {result.get('size_after_mb', 0):.2f} MB")
                else:
                    console.print(f"[red]ERROR[/red] {result.get('error')}")
                    sys.exit(1)

            return

        # Reindex mode
        console.print("Indexing .memory/ content...")

        # Always ensure database exists
        if not indexer.index_path.exists():
            console.print("Creating database...")
            indexer.create_database()
        elif force:
            console.print("Force rebuilding database...")
            indexer.create_database()

        with console.status("[bold green]Indexing files..."):
            total_entries = indexer.index_all(exclude_archive=True)

        console.print(f"[green]Indexed {total_entries} entries[/green]")
        console.print(f"Index location: {indexer.index_path}")

    except ImportError:
        console.print("[red]ERROR[/red] SQLite indexing module not available")
        console.print("This feature requires the db module")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]ERROR[/red] Indexing failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def archive(
    target: str = typer.Argument(..., help="Target: 'decisions', 'current', 'plans'"),
    phase: int = typer.Option(None, "--phase", help="Phase number to archive (backwards compat)"),
    up_to: int = typer.Option(None, "--up-to", help="Archive decisions up to this number (e.g., 25 = #1-#25)"),
    keep_recent: int = typer.Option(None, "--keep-recent", help="Keep only N most recent decisions"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be archived without doing it"),
):
    """Archive completed documentation (marchive command).

    Examples:
        marchive decisions                    # Keep recent 10 (default)
        marchive decisions --keep-recent 15   # Keep recent 15
        marchive decisions --up-to 25         # Archive #1-25
        marchive decisions --phase 5          # Archive Phase 1-5 (old style)
        marchive current --phase 5            # Archive Phase 5 current.md
        marchive plans                        # Move PLAN-*.md to archive
        marchive decisions --dry-run          # Preview
    """
    try:
        from memory_tool.core.archiver import Archiver, ArchiverError
        from memory_tool.utils.config import Config

        archiver = Archiver()

        if target == "decisions":
            # Validate mutually exclusive options
            options_provided = sum([phase is not None, up_to is not None, keep_recent is not None])

            if options_provided > 1:
                console.print("[red]ERROR[/red] Only one of --phase, --up-to, or --keep-recent can be specified")
                sys.exit(1)

            # Determine which mode to use
            if phase is not None:
                # Mode: Phase-based (backwards compat)
                mode = "phase"
                value = phase
            elif up_to is not None:
                # Mode: Decision number-based
                mode = "up-to"
                value = up_to
            else:
                # Mode: Keep recent (default or explicit)
                mode = "keep-recent"
                if keep_recent is None:
                    # Use default from config
                    config = Config()
                    value = config.get("modules.archive_keep_recent", 10)
                else:
                    value = keep_recent

            try:
                # Call appropriate archiver method
                if mode == "phase":
                    archive_path, num_archived = archiver.archive_decisions(value, dry_run)
                elif mode == "up-to":
                    archive_path, num_archived = archiver.archive_decisions_by_number(value, dry_run)
                else:  # keep-recent
                    archive_path, num_archived = archiver.archive_decisions_by_count(value, dry_run)

                if dry_run:
                    console.print(f"[cyan]Would archive {num_archived} decisions to:[/cyan]")
                    console.print(f"  {archive_path.relative_to(Path.cwd())}")
                    console.print(f"\n[dim]Mode: {mode}={value}[/dim]")
                else:
                    console.print(f"[green]OK[/green] Archived {num_archived} decisions")
                    console.print(f"  → {archive_path.relative_to(Path.cwd())}")
                    console.print(f"\n[dim]Backup: decisions.md.bak[/dim]")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif target == "current":
            # Archive current.md
            if not phase:
                console.print("[red]ERROR[/red] --phase required for current")
                console.print("[dim]Example: marchive current --phase 5[/dim]")
                sys.exit(1)

            try:
                archive_path = archiver.archive_current(phase, dry_run)

                if dry_run:
                    console.print(f"[cyan]Would archive current.md to:[/cyan]")
                    console.print(f"  {archive_path.relative_to(Path.cwd())}")
                else:
                    console.print(f"[green]OK[/green] Archived current.md")
                    console.print(f"  → {archive_path.relative_to(Path.cwd())}")
                    console.print(f"\n[dim]Backup: current.md.bak[/dim]")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif target == "plans":
            # Archive PLAN files
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
def completion(
    action: str = typer.Argument(..., help="Action: generate, install, uninstall, status"),
    shell: str = typer.Argument(None, help="Shell: bash, zsh, powershell"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    to_profile: bool = typer.Option(False, "--profile", help="Append to shell profile"),
):
    """Manage shell completion scripts (mcompletion command).

    Actions:
        generate: Generate completion script for shell
        install: Install completion script to default location
        uninstall: Remove completion script
        status: Check installation status

    Examples:
        mcompletion generate bash          # Print bash completion
        mcompletion install bash           # Install bash completion
        mcompletion install zsh --profile  # Add to .zshrc
        mcompletion status bash            # Check if installed
        mcompletion uninstall bash         # Remove completion
    """
    try:
        from memory_tool.utils.completion import CompletionManager

        manager = CompletionManager()

        # Action: generate
        if action == "generate":
            if not shell:
                console.print("[red]ERROR[/red] Shell type required")
                console.print("[dim]Usage: mcompletion generate <shell>[/dim]")
                sys.exit(1)

            try:
                script = manager.generate_completion(shell)
                console.print(script)
            except Exception as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        # Action: install
        elif action == "install":
            if not shell:
                console.print("[red]ERROR[/red] Shell type required")
                console.print("[dim]Usage: mcompletion install <shell>[/dim]")
                sys.exit(1)

            try:
                output_path = Path(output) if output else None
                installed_path = manager.install_completion(
                    shell,
                    output_file=output_path,
                    append_to_profile=to_profile
                )

                console.print(f"[green]OK[/green] Completion installed:")
                console.print(f"  → {installed_path}")

                if to_profile:
                    console.print("\n[cyan]Reload your shell or run:[/cyan]")
                    console.print(f"  source {installed_path}")
                else:
                    console.print("\n[cyan]Reload your shell for changes to take effect[/cyan]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        # Action: uninstall
        elif action == "uninstall":
            if not shell:
                console.print("[red]ERROR[/red] Shell type required")
                console.print("[dim]Usage: mcompletion uninstall <shell>[/dim]")
                sys.exit(1)

            try:
                removed = manager.uninstall_completion(shell)

                if removed:
                    console.print(f"[green]OK[/green] Completion removed for {shell}")
                    console.print("[cyan]Reload your shell for changes to take effect[/cyan]")
                else:
                    console.print(f"[yellow]No completion found for {shell}[/yellow]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        # Action: status
        elif action == "status":
            if not shell:
                # Check all shells
                shells = ["bash", "zsh", "powershell"]
                console.print("[bold cyan]Completion Status:[/bold cyan]\n")

                for sh in shells:
                    installed = manager.check_installation(sh)
                    status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                    status_text = "Installed" if installed else "Not installed"
                    console.print(f"  {status_icon} {sh:12} {status_text}")

            else:
                # Check specific shell
                installed = manager.check_installation(shell)

                if installed:
                    console.print(f"[green]OK[/green] Completion installed for {shell}")
                else:
                    console.print(f"[yellow]Completion not installed for {shell}[/yellow]")
                    console.print("\n[cyan]To install:[/cyan]")
                    console.print(f"  mcompletion install {shell}")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("[dim]Valid actions: generate, install, uninstall, status[/dim]")
            sys.exit(1)

    except ImportError:
        console.print("[red]ERROR[/red] Completion module not available")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def browse(
    query: str = typer.Argument(None, help="Initial search query"),
):
    """Interactive TUI search browser (mbrowse command).

    Launch an interactive terminal interface for searching and browsing
    timeline entries. Provides keyboard navigation, detail view, and
    vim-style keybindings.

    Keybindings:
        /: Focus search input
        Enter: Show detail view
        Esc: Close detail view
        q: Quit application
        j/k: Navigate results (Vim-style)

    Examples:
        mbrowse                    # Launch browser
        mbrowse "search query"     # Launch with query
    """
    try:
        # Check if textual is available
        try:
            from memory_tool.tui import SearchBrowser
        except ImportError:
            console.print("[red]ERROR[/red] TUI feature not available")
            console.print("Install with: pip install memory-tool[tui]")
            console.print("Or: pip install textual>=0.47.0")
            sys.exit(1)

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        # Launch TUI app (pass project root, not .memory path)
        from memory_tool.tui.search_browser import run_search_browser
        run_search_browser(base_path=Path.cwd(), initial_query=query)

    except KeyboardInterrupt:
        console.print("\n[yellow]Browser closed[/yellow]")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Browser failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def plan(
    action: str = typer.Argument(..., help="Action: create, list, show, add, done, delete"),
    name: str = typer.Argument(None, help="Plan name"),
    title: str = typer.Argument(None, help="Task title (for 'add' action)"),
    description: str = typer.Option("", "--desc", "-d", help="Plan description"),
    due_date: str = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
    tags: List[str] = typer.Option([], "--tag", "-t", help="Tags"),
):
    """Manage plans and tasks (mplan command).

    Actions:
        create: Create a new plan
        list: List all plans
        show: Show plan details
        add: Add task to plan
        done: Mark task as completed
        delete: Delete a plan

    Examples:
        mplan create "Project Alpha" --desc "Main project plan"
        mplan list
        mplan show "Project Alpha"
        mplan add "Project Alpha" "Implement feature X"
        mplan done "Project Alpha" "Implement feature X"
        mplan delete "Project Alpha"
    """
    try:
        from memory_tool.planner import PlanManager, Task, TaskStatus
        from datetime import datetime

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        manager = PlanManager(base_path=memory_path)

        # Action: create
        if action == "create":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan create <name> [options][/dim]")
                sys.exit(1)

            # Parse due date
            due = None
            if due_date:
                try:
                    due = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print(f"[red]ERROR[/red] Invalid date format: {due_date}")
                    console.print("[dim]Use YYYY-MM-DD format[/dim]")
                    sys.exit(1)

            # Create plan
            plan_obj = manager.create_plan(
                name=name,
                description=description,
                due_date=due,
                tags=tags
            )

            # Save plan
            filepath = manager.save_plan(plan_obj)
            console.print(f"[green]OK[/green] Plan created:")
            console.print(f"  → {filepath.relative_to(Path.cwd())}")

        # Action: list
        elif action == "list":
            plans = manager.list_plans()

            if not plans:
                console.print("[yellow]No plans found[/yellow]")
                console.print("[dim]Create a plan with: mplan create <name>[/dim]")
                return

            console.print("[bold cyan]Plans:[/bold cyan]\n")
            for plan_info in plans:
                completion = plan_info['completion']
                status_color = "green" if completion >= 100 else "yellow" if completion >= 50 else "red"
                console.print(f"  [{status_color}]{completion:5.1f}%[/{status_color}] {plan_info['name']}")
                console.print(f"         {plan_info['tasks']} tasks | Modified: {plan_info['modified'].strftime('%Y-%m-%d %H:%M')}")

        # Action: show
        elif action == "show":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan show <name>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Load and display plan
            plan_obj = manager.load_plan(plan_file)
            console.print(plan_obj.to_markdown())

        # Action: add
        elif action == "add":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title required")
                console.print("[dim]Usage: mplan add <plan-name> <task-title>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Load plan
            plan_obj = manager.load_plan(plan_file)

            # Add task
            task = Task(title=title, tags=tags)
            plan_obj.add_task(task)

            # Save plan
            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task added to '{plan_obj.name}'")
            console.print(f"  - [ ] {title}")

        # Action: done
        elif action == "done":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title required")
                console.print("[dim]Usage: mplan done <plan-name> <task-title>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Load plan
            plan_obj = manager.load_plan(plan_file)

            # Find and mark task as done
            task_found = False
            for task in plan_obj.tasks:
                if task.title.lower() == title.lower():
                    task.mark_completed()
                    task_found = True
                    break

            if not task_found:
                console.print(f"[red]ERROR[/red] Task not found: {title}")
                sys.exit(1)

            # Save plan
            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task completed in '{plan_obj.name}'")
            console.print(f"  - [x] {title}")

        # Action: delete
        elif action == "delete":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan delete <name>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Delete plan
            manager.delete_plan(plan_file)
            console.print(f"[green]OK[/green] Plan deleted: {name}")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("[dim]Valid actions: create, list, show, add, done, delete[/dim]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def tutorial(
    lesson: str = typer.Argument(None, help="Lesson ID to show (optional)"),
    list_lessons: bool = typer.Option(False, "--list", "-l", help="List available lessons"),
):
    """Interactive tutorial for memory_tool (mtutorial command).

    Learn how to use memory_tool commands with step-by-step tutorials.

    Examples:
        mtutorial                  # Show interactive menu
        mtutorial basics           # Show basics lesson
        mtutorial --list           # List all lessons
    """
    try:
        from memory_tool.utils.tutorial import Tutorial

        tut = Tutorial()

        if list_lessons:
            tut.list_lessons()
        else:
            tut.run(lesson_id=lesson)

    except KeyboardInterrupt:
        console.print("\n[yellow]Tutorial closed[/yellow]")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Tutorial failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """Memory Tool - Time-Space Integrated Knowledge System."""
    if version:
        from memory_tool import __version__
        console.print(f"Memory Tool v{__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                "[bold cyan]Memory Tool[/bold cyan]\n\n"
                "Time-Space Integrated Knowledge System\n"
                "For Claude Code integration\n\n"
                "[dim]Use --help to see available commands[/dim]",
                border_style="cyan",
            )
        )


if __name__ == "__main__":
    app()
