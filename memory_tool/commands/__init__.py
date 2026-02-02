"""CLI commands package for Memory Tool.

This package contains modularized CLI commands organized by functionality:
- timeline: record, today, week, month, days, sort, review
- modules: module, archive, browse
- search: search, check, index
- planning: plan, summary
- context: context, map
- notion: all Notion integration commands
- system: init, status, alias, completion, tutorial, hooks, migrate_timeline
- qa: ask (RAG-based Q&A)
"""

from memory_tool.commands.common import app, console

# Import all command modules to register them with the app
# The order doesn't matter since all commands use @app.command()
from memory_tool.commands import timeline
from memory_tool.commands import modules
from memory_tool.commands import search
from memory_tool.commands import planning
from memory_tool.commands import context
from memory_tool.commands import notion
from memory_tool.commands import system
from memory_tool.commands import qa
from memory_tool.commands import help
from memory_tool.commands import federation
from memory_tool.commands import tag

__all__ = ["app", "console"]
