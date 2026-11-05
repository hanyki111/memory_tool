"""Review CLI: move what is worth keeping from the timeline into documents."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, NoReturn, Optional, Tuple

import click
import typer

from memory_tool.commands.common import app, console
from memory_tool.review import session, store, writer
from memory_tool.review.store import Item, Review, ReviewError
from memory_tool.review.text import say
from memory_tool.utils.paths import display_path, get_base_path, get_project_root

review_app = typer.Typer(
    name="review",
    help="Review recent timeline entries (mreview command).",
    invoke_without_command=True,
)
app.add_typer(review_app, name="review")

#: A choice: what the user types, what it says, and what it does. The action
#: returns False when the review should pause.
Choice = Tuple[str, str, Callable[[], bool]]


def _print(text: str = "") -> None:
    """Print text that may hold brackets from entries, which are not markup."""
    console.print(text, markup=False, highlight=False)


def _fail(message: str) -> NoReturn:
    console.print(f"[red]ERROR[/red] {message}", highlight=False)
    sys.exit(1)


def _base():
    base = get_base_path()
    if not base.exists():
        _fail(say("Knowledge base not found. Run 'minit' first.", "지식 베이스가 없습니다. 먼저 minit을 실행해 주세요."))
    return base


def _parse_since(since: Optional[str]) -> Optional[datetime]:
    if not since:
        return None
    try:
        return datetime.strptime(since, "%Y-%m-%d")
    except ValueError:
        _fail(say(f"Invalid date: {since}. Use YYYY-MM-DD.", f"날짜 형식이 잘못되었습니다: {since}. YYYY-MM-DD로 입력해 주세요."))


def _ask(choices: List[Choice], default: Optional[str] = None) -> bool:
    """Show choices until one is picked, then run it.

    Args:
        choices: The choices
        default: The key that Enter picks

    Returns:
        What the chosen action returned.
    """
    for key, label, _ in choices:
        _print(f"  {key}. {label}")

    actions = {key: action for key, _, action in choices}

    while True:
        answer = typer.prompt(say("Choice", "선택"), default=default).strip().lower()
        if answer in actions:
            return actions[answer]()
        _print(say("Please pick one of the choices.", "목록에서 골라 주세요."))


def _pause(review: Review) -> bool:
    store.save_review(review)

    if review.is_done:
        _print(say(
            "Left as being written. Run 'mreview done' when it is finished.",
            "작성 중으로 남겨 두었습니다. 다 쓰면 mreview done을 실행해 주세요.",
        ))
        return False

    _print(say(
        f"Paused. Your choices are saved in {display_path(review.path)}. Run mreview to continue.",
        f"일시정지했습니다. 선택 내용은 {display_path(review.path)}에 저장했습니다. mreview로 이어 갈 수 있습니다.",
    ))
    return False


def _show_item(review: Review, item: Item) -> None:
    open_count = len(review.open_items())
    _print()
    _print(f"[{item.number}] {store.item_label(item)}")

    if item.why:
        _print(f"    {item.why}")
    if item.evidence:
        _print(say(f"    Entries: {', '.join(item.evidence)}", f"    근거 기록: {', '.join(item.evidence)}"))
    if item.split_note:
        lines, sections = item.split_note["lines"], item.split_note["sections"]
        _print(say(
            f"    Note: this document has {lines} lines and {sections} headings, so it may be worth splitting.",
            f"    참고: 이 문서는 {lines}줄이고 제목이 {sections}개여서 분할 후보입니다.",
        ))
    if item.state == store.STATE_WRITING:
        _print(say("    You were writing this.", "    작성 중인 항목입니다."))
    elif item.carried:
        _print(say("    Put off in an earlier review.", "    이전 리뷰에서 미룬 항목입니다."))
    if not review.can_defer():
        _print(say(
            f"    {open_count} items remain open, so nothing can be put off until {store.MAX_OPEN_ITEMS} remain.",
            f"    남은 항목이 {open_count}건이므로, {store.MAX_OPEN_ITEMS}건이 될 때까지 미룰 수 없습니다.",
        ))


def _settle(review: Review, change: Callable[[Review, int], Item], number: int) -> bool:
    change(review, number)
    store.save_review(review)
    return True


def _pick_tool(title: str, tool: Optional[str]) -> str:
    """Decide how to write: the tool given, or the menu.

    Returns:
        A tool key or ``writer.SOLO``.
    """
    if tool:
        return writer.resolve_choice(tool)

    installed = writer.installed_tools()
    default = writer.default_tool(installed)

    _print(say(f'How do you want to write "{title}"?', f'"{title}"을(를) 어떻게 쓰시겠습니까?'))

    options = []
    for candidate in installed:
        options.append(candidate.key)
        mark = say(" (default)", " (기본값)") if candidate is default else ""
        _print(f"  {len(options)}. {candidate.name}{mark}")

    options.append(writer.SOLO)
    mark = "" if default else say(" (default)", " (기본값)")
    _print(f"  {len(options)}. {say('On my own', '혼자 쓰기')}{mark}")

    default_number = options.index(default.key if default else writer.SOLO) + 1

    while True:
        answer = typer.prompt(say("Choice", "선택"), default=str(default_number)).strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        _print(say("Please pick one of the choices.", "목록에서 골라 주세요."))


def _document_for_solo(base: Path, item: Item) -> Path:
    """Find the document to edit, creating a new one now that writing starts."""
    from memory_tool.core.module import ModuleError, ModuleManager
    from memory_tool.utils.module_docs import resolve_module_document

    modules = base / "modules"

    if item.kind == store.KIND_UPDATE:
        document = resolve_module_document(modules / str(item.target))
        if document is None:
            raise ReviewError(say(f"Document not found: {item.target}", f"문서를 찾을 수 없습니다: {item.target}"))
        return document

    manager = ModuleManager()

    while True:
        name = typer.prompt(say("Document path", "문서 경로"), default=writer.suggested_path(item.title)).strip()
        try:
            if not manager.module_exists(name):
                manager.create(name, description=item.why, doc_type=item.doc_type)
            break
        except ModuleError as e:
            _print(str(e))

    document = resolve_module_document(modules / name)
    if document is None:
        raise ReviewError(say(f"Document not found: {name}", f"문서를 찾을 수 없습니다: {name}"))
    return document


def _write_item(base: Path, review: Review, item: Item, tool: Optional[str]) -> None:
    """Mark an item as being written and start writing it.

    The state is saved first, so if anything fails the item is asked about again.
    """
    store.start_writing(review, item.number)
    store.save_review(review)

    choice = _pick_tool(item.title, tool)

    if choice == writer.SOLO:
        document = _document_for_solo(base, item)
        for line in writer.evidence_lines(base, item.evidence):
            _print(f"  {line}")
        _print(f"-> {display_path(document)}")
        writer.open_in_editor(document)
        return

    selected = next(candidate for candidate in writer.TOOLS if candidate.key == choice)
    _print(say(f"Starting {selected.name}. Leave it when you are done.", f"{selected.name}을(를) 실행합니다. 다 쓰면 종료해 주세요."))
    writer.write_with_tool(selected, base, get_project_root(), review, item)


def _write_now(review: Review, item: Item, tool: Optional[str]) -> bool:
    """Write an item. The next question asks how it went."""
    _write_item(get_base_path(), review, item, tool)
    return True


def _item_choices(review: Review, item: Item, tool: Optional[str]) -> List[Choice]:
    """Offer what can be done with an item right now."""
    number = item.number
    write = lambda: _write_now(review, item, tool)
    written = lambda: _settle(review, store.mark_written, number)
    later = lambda: _settle(review, store.defer, number)
    rejected = lambda: _settle(review, store.reject, number)
    pause = lambda: _pause(review)

    if item.state == store.STATE_WRITING:
        options = [
            (say("Written", "썼음"), written),
            (say("Still writing (pause)", "아직 쓰는 중 (일시정지)"), pause),
            (say("Put off", "미룸"), later) if review.can_defer() else None,
            (say("Reject", "거절"), rejected),
        ]
    elif item.carried:
        options = [
            (say("Written", "썼음"), written),
            (say("Keep for later", "계속 대기"), later) if review.can_defer() else None,
            (say("Drop", "버림"), rejected),
            (say("Write now", "지금 쓰기"), write),
        ]
    else:
        options = [
            (say("Write now", "지금 쓰기"), write),
            (say("Write later", "나중에 쓰기"), later) if review.can_defer() else None,
            (say("Reject", "거절"), rejected),
        ]

    available = [option for option in options if option is not None]
    choices: List[Choice] = [(str(i), label, action) for i, (label, action) in enumerate(available, 1)]

    if item.state != store.STATE_WRITING:
        choices.append(("p", say("Pause", "일시정지"), pause))

    return choices


def _reflect(review: Review) -> bool:
    """Offer the optional reflection, once the items are settled.

    Returns:
        False if the user paused the review.
    """
    if review.reflection != store.REFLECTION_OPEN:
        return True

    if not review.entry_count:
        review.reflection = store.REFLECTION_SKIPPED
        store.save_review(review)
        return True

    def finish_with(state: str) -> bool:
        review.reflection = state
        store.save_review(review)
        return True

    def with_tool(tool: writer.WritingTool) -> bool:
        _print(say(f"Starting {tool.name}. Leave it when you are done.", f"{tool.name}을(를) 실행합니다. 다 쓰면 종료해 주세요."))
        writer.reflect_with_tool(tool, get_base_path(), get_project_root(), review)
        return finish_with(store.REFLECTION_WRITTEN)

    def alone() -> bool:
        _print(f"-> {display_path(review.path)}")
        writer.open_in_editor(review.path)
        return finish_with(store.REFLECTION_WRITTEN)

    _print()
    _print(say(
        f"Reflection (optional): {review.entry_count} entries on {review.active_days} days.",
        f"돌아보기(선택 사항): 활동 {review.active_days}일, 기록 {review.entry_count}건입니다.",
    ))

    installed = writer.installed_tools()
    default = writer.default_tool(installed)
    # A default-argument binding, so that each choice keeps its own tool.
    choices: List[Choice] = [
        (
            str(number),
            tool.name + (say(" (default)", " (기본값)") if tool is default else ""),
            lambda tool=tool: with_tool(tool),
        )
        for number, tool in enumerate(installed, 1)
    ]
    choices.append((str(len(choices) + 1), say("On my own", "혼자 쓰기"), alone))
    choices.append(("s", say("Skip", "건너뛰기"), lambda: finish_with(store.REFLECTION_SKIPPED)))
    choices.append(("p", say("Pause", "일시정지"), lambda: _pause(review)))

    return _ask(choices, default="1" if default else None)


def _finish(review: Review) -> None:
    review.status = store.STATUS_DONE
    store.save_review(review)

    written = sum(item.state == store.STATE_WRITTEN for item in review.items)
    later = len(review.open_items())
    rejected = sum(item.state == store.STATE_REJECTED for item in review.items)

    _print()
    _print(say(
        f"Review finished: {written} written, {later} for later, {rejected} rejected.",
        f"리뷰를 마쳤습니다. 썼음 {written}건, 대기 {later}건, 거절 {rejected}건입니다.",
    ))
    _print(f"-> {display_path(review.path)}")


def _work_through(review: Review, tool: Optional[str]) -> None:
    """Go through a review's items, saving after every choice."""
    _print(say(f"Review {review.name}: {review.start} to {review.end}", f"리뷰 {review.name}: {review.start} ~ {review.end}"))
    _print(say(
        f"{review.entry_count} entries on {review.active_days} days.",
        f"활동 {review.active_days}일, 기록 {review.entry_count}건입니다.",
    ))
    if review.dropped:
        _print(say(
            f"{review.dropped} more candidates were left out. Their entries stay in the timeline.",
            f"이 밖의 후보 {review.dropped}건은 제외했습니다. 원본은 타임라인에 남아 있습니다.",
        ))

    while True:
        waiting = review.undecided_items()
        if not waiting:
            break
        _show_item(review, waiting[0])
        if not _ask(_item_choices(review, waiting[0], tool)):
            return

    if _reflect(review):
        _finish(review)


@review_app.callback()
def review(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, "--since", help="Start of the period (YYYY-MM-DD), for a new review"),
    with_tool: Optional[str] = typer.Option(None, "--with", help="How to write, skipping the menu: claude, codex, antigravity or solo"),
):
    """Find what is worth moving from the timeline into documents.

    With no command, starts a review of the entries since the last one, or
    continues the review in progress.

    Examples:
        mreview                       # Start or continue a review
        mreview --since 2026-10-01    # Start a review from a chosen date
        mreview list                  # Items waiting to be written
        mreview write 2               # Write item 2 now
        mreview write 2 --with codex  # The same, skipping the menu
        mreview done 2                # Mark item 2 as written
    """
    if ctx.invoked_subcommand:
        return

    base = _base()
    since_date = _parse_since(since)

    try:
        if with_tool:
            writer.resolve_choice(with_tool)

        current = store.latest_review(base)
        if since_date and current and not current.is_done:
            _print(say(
                f"Review {current.name} is in progress, so --since is ignored.",
                f"리뷰 {current.name}이(가) 진행 중이므로 --since를 무시합니다.",
            ))

        if not (current and not current.is_done):
            _print(say("Reading the timeline and asking for proposals...", "타임라인을 읽고 제안을 받는 중입니다..."))

        active = session.open_review(base, since=since_date)

        if active is None:
            _print(say("No new entries and nothing waiting.", "새 기록도, 대기 중인 항목도 없습니다."))
            return

        _work_through(active, with_tool)
    except click.exceptions.Abort:
        _print()
        _print(say("Paused. Run mreview to continue.", "일시정지했습니다. mreview로 이어 갈 수 있습니다."))
    except ReviewError as e:
        _fail(str(e))


@review_app.command("list")
def list_items():
    """Show the items waiting to be written."""
    try:
        latest = store.latest_review(_base())
    except ReviewError as e:
        _fail(str(e))

    waiting = latest.open_items() if latest else []

    if not waiting:
        _print(say("Nothing is waiting.", "대기 중인 항목이 없습니다."))
        return

    for item in waiting:
        _print(f"{item.number}. [{store.state_label(item)}] {store.item_label(item)}")


@review_app.command("write")
def write(
    number: int = typer.Argument(..., help="Item number from 'mreview list'"),
    with_tool: Optional[str] = typer.Option(None, "--with", help="How to write, skipping the menu: claude, codex, antigravity or solo"),
):
    """Write a waiting item now, without waiting for the next review."""
    base = _base()

    try:
        latest = store.latest_review(base)
        if latest is None:
            _fail(say("There is no review yet.", "아직 리뷰가 없습니다."))

        item = latest.item(number)
        if not item.is_open:
            _fail(say(f"Item {number} is already settled.", f"{number}번 항목은 이미 처리되었습니다."))
        if with_tool:
            writer.resolve_choice(with_tool)

        _write_item(base, latest, item, with_tool)

        _print()
        _print(say("How did it go?", "어떻게 되었나요?"))
        _ask(_item_choices(latest, item, None))
    except click.exceptions.Abort:
        _print()
        _print(say("Left as being written.", "작성 중으로 남겨 두었습니다."))
    except ReviewError as e:
        _fail(str(e))


@review_app.command("done")
def done(number: int = typer.Argument(..., help="Item number from 'mreview list'")):
    """Mark an item as written."""
    try:
        latest = store.latest_review(_base())
        if latest is None:
            _fail(say("There is no review yet.", "아직 리뷰가 없습니다."))

        item = store.mark_written(latest, number)
        store.save_review(latest)
    except ReviewError as e:
        _fail(str(e))

    _print(say(f"Marked as written: {item.title}", f"썼음으로 표시했습니다: {item.title}"))
