"""entry: find, edit or delete one timeline entry, named by date, time and text.

For programs that list the timeline and change an entry afterwards, such as
the phone app. An entry is named by what the program saw; if the file changed
since, the entry is not found and nothing changes, so a newer edit is never
overwritten. People editing by hand use ``medit``.
"""

import sys
from typing import Optional

import typer

from memory_tool.commands import json_output
from memory_tool.commands.common import app, console, opt_str
from memory_tool.core.timeline import (
    DistantPastWarning,
    EntryNotFound,
    FutureTimeError,
    Timeline,
    TimelineError,
    entry_tags,
)

entry_app = typer.Typer(
    help="Find, edit or delete one timeline entry by date, time and text (for programs; people use medit).",
    no_args_is_help=True,
)
app.add_typer(entry_app, name="entry")

DATE_HELP = "The entry's date (YYYY-MM-DD)"
TIME_HELP = "The entry's time (HH:MM)"
TEXT_HELP = "The entry's text, as written or as typed (tags may be in either form)"
JSON_HELP = "Print the result as one line of JSON"


def _entry(entry: dict) -> dict:
    return {**entry, "tags": entry_tags(entry["text"])}


def _fail(as_json: bool, code: str, message: str) -> None:
    if as_json:
        json_output.fail(code, message)
    console.print(f"[red]ERROR[/red] {message}", markup=True, highlight=False)
    sys.exit(1)


def _run(as_json: bool, action):
    """Run an entry action, turning its errors into the shared failure codes."""
    try:
        return action()
    except EntryNotFound as e:
        _fail(as_json, json_output.NOT_FOUND, str(e))
    except FutureTimeError as e:
        _fail(as_json, json_output.FUTURE_TIME, str(e))
    except DistantPastWarning as e:
        _fail(as_json, json_output.DISTANT_PAST, f"{e} Use --force to move it anyway.")
    except ValueError as e:
        _fail(as_json, json_output.INVALID_ARGUMENT, str(e))
    except TimelineError as e:
        _fail(as_json, json_output.FAILED, str(e))


@entry_app.command("find")
def find(
    date: str = typer.Option(..., "--date", help=DATE_HELP),
    time: str = typer.Option(..., "--time", help=TIME_HELP),
    text: str = typer.Option(..., "--text", help=TEXT_HELP),
    as_json: bool = typer.Option(False, "--json", help=JSON_HELP),
):
    """Say whether an entry is in the timeline.

    "fix #bug" finds the entry recorded as "[bug] fix", since record writes it so.

    Example:
        memory_tool entry find --date 2026-11-07 --time 14:02 --text "fix #bug" --json
    """
    timeline = Timeline()

    def look():
        _, entries, position = timeline.find_entry(date, time, text)
        if position is None:
            return None
        found = entries[position]
        return {"date": date, "time": Timeline._normal_time(found["time"]), "text": found["message"]}

    found = _run(as_json, look)
    if as_json:
        if found is None:
            json_output.succeed(found=False)
        else:
            json_output.succeed(found=True, entry=_entry(found))
        return
    if found is None:
        console.print(f"No entry at {date} {time} with that text.", markup=False, highlight=False)
        sys.exit(1)
    console.print(f"- {found['time']} | {found['text']}", markup=False, highlight=False)


@entry_app.command("edit")
def edit(
    date: str = typer.Option(..., "--date", help=DATE_HELP),
    time: str = typer.Option(..., "--time", help=TIME_HELP),
    text: str = typer.Option(..., "--text", help=TEXT_HELP),
    new_date: Optional[str] = typer.Option(None, "--new-date", help="Move the entry to this date (YYYY-MM-DD)"),
    new_time: Optional[str] = typer.Option(None, "--new-time", help="Change the time (HH:MM)"),
    new_text: Optional[str] = typer.Option(None, "--new-text", help="Change the text; tags are written as record writes them"),
    force: bool = typer.Option(False, "--force", "-f", help="Allow a date more than a year ago"),
    as_json: bool = typer.Option(False, "--json", help=JSON_HELP),
):
    """Change an entry's date, time or text.

    Lines written by hand under the entry are kept. A new date or time is
    checked as record checks it.

    Example:
        memory_tool entry edit --date 2026-11-07 --time 00:30 --text "late note" --new-date 2026-11-06 --new-time 23:50
    """
    timeline = Timeline()
    before, after = _run(as_json, lambda: timeline.edit_entry(
        date, time, text,
        new_date=opt_str(new_date), new_time=opt_str(new_time), new_text=opt_str(new_text), force=force,
    ))
    if as_json:
        json_output.succeed(entry=_entry(after), previous=_entry(before))
        return
    console.print(f"[green]OK[/green] {after['date']} {after['time']} | ", end="")
    console.print(after["text"], markup=False, highlight=False)


@entry_app.command("delete")
def delete(
    date: str = typer.Option(..., "--date", help=DATE_HELP),
    time: str = typer.Option(..., "--time", help=TIME_HELP),
    text: str = typer.Option(..., "--text", help=TEXT_HELP),
    as_json: bool = typer.Option(False, "--json", help=JSON_HELP),
):
    """Delete an entry. Lines written by hand under it are kept.

    Example:
        memory_tool entry delete --date 2026-11-07 --time 14:02 --text "test entry"
    """
    timeline = Timeline()
    deleted = _run(as_json, lambda: timeline.delete_entry(date, time, text))
    if as_json:
        json_output.succeed(entry=_entry(deleted))
        return
    console.print(f"[green]OK[/green] Deleted {deleted['date']} {deleted['time']} | ", end="")
    console.print(deleted["text"], markup=False, highlight=False)
