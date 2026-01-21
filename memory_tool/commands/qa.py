"""Q&A CLI commands for Memory Tool."""

import sys
from typing import Optional

import typer

from memory_tool.commands.common import app, console, opt_str


@app.command(name="ask")
def memory_ask(
    question: str = typer.Argument(..., help="Natural language question about your memory"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider (anthropic, ollama, claude-cli, gemini-cli)"),
    simple: bool = typer.Option(False, "--simple", "-s", help="Use simple keyword search (not agentic)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed process (agent steps, sources)"),
    no_timeline: bool = typer.Option(False, "--no-timeline", help="Don't search timeline (simple mode only)"),
    no_modules: bool = typer.Option(False, "--no-modules", help="Don't search modules (simple mode only)"),
    no_plans: bool = typer.Option(False, "--no-plans", help="Don't search plans (simple mode only)"),
    days: int = typer.Option(30, "--days", "-d", help="Days of timeline to search (simple mode only)"),
    max_context: int = typer.Option(15, "--max-context", "-c", help="Maximum context items (simple mode only)"),
):
    """Ask a question about your memory (mask command).

    Uses an AI agent that can:
    1. Interpret your question
    2. Select and execute appropriate memory tools
    3. Synthesize results into a coherent answer

    Examples:
        mask "어제 무엇을 했나요?"
        mask "What did I work on last week?"
        mask "What decisions were made about the database?"
        mask "지난주 plan 진행상황은?"
        mask "CLI 리팩토링 관련 내용 찾아줘"
        mask "memory-tool 모듈 현재 상태는?"

    Options:
        mask "question" --verbose       # Show agent's reasoning
        mask "question" --simple        # Use simple keyword search (faster)
        mask "question" --provider claude-cli  # Use specific provider
    """
    provider = opt_str(provider)

    try:
        if simple:
            # Use simple keyword-based RAG
            _ask_simple(
                question=question,
                provider=provider,
                verbose=verbose,
                no_timeline=no_timeline,
                no_modules=no_modules,
                no_plans=no_plans,
                days=days,
                max_context=max_context,
            )
        else:
            # Use agentic approach (default)
            _ask_agent(
                question=question,
                provider=provider,
                verbose=verbose,
            )

    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[dim]Available LLM providers:[/dim]")

        from memory_tool.llm.client import LLMClient
        available = LLMClient.list_available_providers()
        if available:
            for p in available:
                console.print(f"  - {p}")
        else:
            console.print("  None configured. Options:")
            console.print("  - Set llm.provider in config.yaml")
            console.print("  - Install Claude CLI: npm install -g @anthropic-ai/claude-code")
            console.print("  - Install Ollama: https://ollama.ai")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


def _ask_agent(
    question: str,
    provider: Optional[str],
    verbose: bool,
):
    """Ask using the agentic approach."""
    from memory_tool.core.memory_agent import MemoryAgent

    agent = MemoryAgent()

    if verbose:
        console.print(f"[dim]Question: {question}[/dim]\n")
        console.print("[bold cyan]Agent Process:[/bold cyan]\n")

    result = agent.ask(
        question=question,
        provider=provider,
        verbose=verbose,
    )

    # Show answer
    if verbose:
        console.print()
    console.print(f"[bold cyan]Answer:[/bold cyan]\n")
    console.print(result.answer)
    console.print()

    # Show metadata
    tools_used = ", ".join(tc.tool for tc in result.tool_calls) or "none"
    console.print(f"[dim]Provider: {result.provider} | Tools: {tools_used}[/dim]")

    # Show tool details if verbose
    if verbose and result.tool_results:
        console.print(f"\n[bold cyan]Tool Results:[/bold cyan]")
        for tr in result.tool_results:
            status = "[green]OK[/green]" if tr.success else f"[red]Error: {tr.error}[/red]"
            console.print(f"  - {tr.tool}({tr.args}): {status}")
            if tr.success and tr.result:
                # Show truncated result
                preview = tr.result[:200].replace("\n", " ")
                if len(tr.result) > 200:
                    preview += "..."
                console.print(f"    [dim]{preview}[/dim]")


def _ask_simple(
    question: str,
    provider: Optional[str],
    verbose: bool,
    no_timeline: bool,
    no_modules: bool,
    no_plans: bool,
    days: int,
    max_context: int,
):
    """Ask using simple keyword-based RAG."""
    from memory_tool.core.memory_qa import MemoryQA

    qa = MemoryQA()

    console.print(f"[dim]Searching memory for: {question}[/dim]\n")

    result = qa.ask(
        question=question,
        search_timeline=not no_timeline,
        search_modules=not no_modules,
        search_plans=not no_plans,
        timeline_days=days,
        max_context_items=max_context,
        provider=provider,
    )

    # Show answer
    console.print(f"[bold cyan]Answer:[/bold cyan]\n")
    console.print(result.answer)
    console.print()

    # Show metadata
    console.print(f"[dim]Provider: {result.provider} | Contexts: {len(result.contexts)}[/dim]")

    # Show sources if verbose
    if verbose and result.contexts:
        console.print(f"\n[bold cyan]Sources:[/bold cyan]")
        for ctx in result.contexts:
            date_str = f" ({ctx.date.strftime('%Y-%m-%d')})" if ctx.date else ""
            console.print(f"  - {ctx.source}{date_str}")


@app.command(name="providers")
def list_providers():
    """List available LLM providers (mproviders command).

    Shows which LLM providers are configured and available for use.
    """
    try:
        from memory_tool.llm.client import LLMClient

        console.print("[bold cyan]LLM Providers:[/bold cyan]\n")

        # Check each provider
        providers = {
            "anthropic": "Claude API (requires API key)",
            "ollama": "Local LLM (requires Ollama server)",
            "claude-cli": "Claude Code CLI (requires CLI installed)",
            "gemini-cli": "Gemini CLI (requires CLI installed)",
        }

        current = LLMClient.get_provider()
        available = LLMClient.list_available_providers()

        for name, desc in providers.items():
            is_current = name == current
            is_available = name in available

            status = "[green]Available[/green]" if is_available else "[dim]Not available[/dim]"
            current_marker = " [yellow](current)[/yellow]" if is_current else ""

            console.print(f"  {name}: {status}{current_marker}")
            console.print(f"    [dim]{desc}[/dim]")

        console.print()
        console.print(f"[dim]Current provider: {current}[/dim]")
        console.print(f"[dim]Configure in: .memory/config.yaml (llm.provider)[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
