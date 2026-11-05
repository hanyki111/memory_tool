"""Review CLI: move what is worth keeping from the timeline into documents."""

import typer

from memory_tool.commands.common import app

review_app = typer.Typer(
    name="review",
    help="Review recent timeline entries (mreview command).",
    invoke_without_command=True,
)
app.add_typer(review_app, name="review")
