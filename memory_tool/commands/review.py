"""Review CLI: reflect on recent entries and settle what to keep in documents."""

import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, List, NoReturn, Optional, Tuple

import click
import typer

from memory_tool.commands.common import app, console
from memory_tool.commands import json_output
from memory_tool.review import collector, session, store, writer
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
            (say("Reject", "남기지 않기"), rejected),
        ]
    elif item.carried:
        options = [
            (say("Written", "썼음"), written),
            (say("Keep for later", "계속 대기"), later) if review.can_defer() else None,
            (say("Drop", "남기지 않기"), rejected),
            (say("Write now", "지금 쓰기"), write),
        ]
    else:
        options = [
            (say("Write now", "지금 쓰기"), write),
            (say("Write later", "나중에 쓰기"), later) if review.can_defer() else None,
            (say("Reject", "남기지 않기"), rejected),
        ]

    available = [option for option in options if option is not None]
    choices: List[Choice] = [(str(i), label, action) for i, (label, action) in enumerate(available, 1)]

    choices.append(("a", say("Add something else to keep", "다른 항목 추가"), lambda: _add_item_by_hand(review)))

    if item.state != store.STATE_WRITING:
        choices.append(("p", say("Pause", "일시정지"), pause))

    return choices


#: What came of one attempt to reflect.
_DONE, _AGAIN, _PAUSED = "done", "again", "paused"


def _reflect(review: Review, tool: Optional[str]) -> Optional[Review]:
    """Reflect on the period, which is how what to keep gets settled.

    Args:
        review: The review
        tool: How to reflect, skipping the menu the first time

    Returns:
        The review as it now stands, since a tool may have added items, or None
        if the user paused.
    """
    if review.reflection != store.REFLECTION_OPEN:
        return review

    if not review.entry_count:
        review.reflection = store.REFLECTION_SKIPPED
        store.save_review(review)
        return review

    base = get_base_path()

    def settle(state: str) -> None:
        nonlocal review
        review.reflection = state
        store.save_review(review)

    def something_changed(text_before: str, items_before: int) -> bool:
        # Leaving a tool or an editor says nothing about whether anything was
        # done, for example after Ctrl+C. Only the file can tell.
        return (
            store.reflection_text(review.path) != text_before
            or len(review.items) != items_before
        )

    def nothing_written() -> str:
        _print()
        _print(say("Nothing was written or added.", "아무것도 적히거나 추가되지 않았습니다."))
        return _AGAIN

    def with_tool(selected: writer.WritingTool) -> str:
        nonlocal review
        text_before, items_before = store.reflection_text(review.path), len(review.items)
        _print(say(f"Starting {selected.name}. Leave it when you are done.", f"{selected.name}을(를) 실행합니다. 다 되면 종료해 주세요."))
        writer.reflect_with_tool(selected, base, get_project_root(), review)
        # The tool added items through another process.
        review = store.load_review(review.path)

        if not something_changed(text_before, items_before):
            return nothing_written()

        review.proposals_pending = False
        settle(store.REFLECTION_WRITTEN)
        return _DONE

    def alone() -> str:
        nonlocal review
        text_before, items_before = store.reflection_text(review.path), len(review.items)
        entries = collector.collect_entries(
            base, collector.parse_time(review.start), collector.parse_time(review.end)
        )
        store.insert_entries(
            review.path, [f"{entry.when:%Y-%m-%d %H:%M} | {entry.text}" for entry in entries]
        )
        _print(f"-> {display_path(review.path)}")
        try:
            writer.open_in_editor(review.path)
        finally:
            store.remove_entries(review.path)
        review = store.load_review(review.path)

        if not something_changed(text_before, items_before):
            return nothing_written()

        settle(store.REFLECTION_WRITTEN)
        return _DONE

    def candidates_only() -> str:
        settle(store.REFLECTION_SKIPPED)
        return _DONE

    _print()
    _print(say(
        f"Reflection: go over {review.entry_count} entries on {review.active_days} days, "
        "and settle what is worth keeping.",
        f"회고: 활동 {review.active_days}일, 기록 {review.entry_count}건을 살펴보고, 무엇을 남길지 정리합니다.",
    ))

    outcome = _AGAIN
    choice = writer.resolve_choice(tool) if tool else None

    if choice == writer.SOLO:
        outcome = alone()
    elif choice:
        outcome = with_tool(next(c for c in writer.TOOLS if c.key == choice))

    while outcome == _AGAIN:
        installed = writer.installed_tools()
        default = writer.default_tool(installed)
        # A default-argument binding, so that each choice keeps its own tool.
        choices: List[Choice] = [
            (
                str(number),
                say(f"Reflect with {candidate.name}", f"{candidate.name}와 회고")
                + (say(" (default)", " (기본값)") if candidate is default else ""),
                lambda candidate=candidate: with_tool(candidate),
            )
            for number, candidate in enumerate(installed, 1)
        ]
        choices.append((str(len(choices) + 1), say("Reflect on my own", "혼자 회고"), alone))
        choices.append(("s", say("Only see the AI's candidates", "AI 후보만 보기"), candidates_only))
        choices.append(("p", say("Pause", "일시정지"), lambda: _PAUSED if not _pause(review) else _PAUSED))
        outcome = _ask(choices, default="1" if default else None)

    return None if outcome == _PAUSED else review


def _ask_for_proposals(review: Review) -> bool:
    """Ask for candidates, which may fail after the reflection was written.

    Returns:
        False if the user paused.
    """
    while True:
        _print(say("Asking for candidates...", "후보를 받는 중입니다..."))
        try:
            session.fill_proposals(get_base_path(), review)
            return True
        except ReviewError as e:
            _print(str(e))
            _print(say(
                "What you wrote is saved in the review file.",
                "쓰신 글은 리뷰 파일에 저장되어 있습니다.",
            ))

        def go_on() -> str:
            review.proposals_pending = False
            store.save_review(review)
            return _DONE

        outcome = _ask(
            [
                ("r", say("Try again", "다시 시도"), lambda: _AGAIN),
                ("c", say("Go on without candidates", "후보 없이 계속"), go_on),
                ("p", say("Pause", "일시정지"), lambda: _PAUSED if not _pause(review) else _PAUSED),
            ],
            default="r",
        )
        if outcome == _DONE:
            return True
        if outcome == _PAUSED:
            return False


def _add_item_by_hand(review: Review) -> bool:
    """Ask what to keep and add it."""
    from memory_tool.utils.module_docs import resolve_module_document

    title = typer.prompt(say("What to keep", "남길 내용")).strip()

    while True:
        target = typer.prompt(
            say("Document to update (Enter: a new document)", "갱신할 문서 (Enter: 새 문서)"),
            default="",
            show_default=False,
        ).strip()
        if not target or resolve_module_document(get_base_path() / "modules" / target) is not None:
            break
        _print(say(f"Document not found: {target}", f"문서를 찾을 수 없습니다: {target}"))

    store.add_item(review, title, target=target or None)
    store.save_review(review)
    return True


def _offer_when_nothing_to_keep(review: Review) -> bool:
    """Say that nothing is listed, and offer the ways to add something.

    Returns:
        False if the user paused.
    """
    _print()
    _print(say(
        "Nothing is listed to keep from this period.",
        "이 기간에서 남길 것으로 정한 항목이 없습니다.",
    ))

    def ask_ai() -> bool:
        return _ask_for_proposals(review)

    return _ask(
        [
            ("1", say("Finish (default)", "끝내기 (기본값)"), lambda: True),
            ("2", say("Get the AI's candidates", "AI 후보 받기"), ask_ai),
            ("a", say("Add one myself", "직접 추가"), lambda: _add_item_by_hand(review)),
            ("p", say("Pause", "일시정지"), lambda: _pause(review)),
        ],
        default="1",
    )


def _finish(review: Review) -> None:
    review.status = store.STATUS_DONE
    store.save_review(review)

    written = sum(item.state == store.STATE_WRITTEN for item in review.items)
    later = len(review.open_items())
    rejected = sum(item.state == store.STATE_REJECTED for item in review.items)

    reflection = {
        store.REFLECTION_WRITTEN: say("written", "작성함"),
        store.REFLECTION_SKIPPED: say("skipped", "건너뜀"),
    }.get(review.reflection, say("not done", "하지 않음"))
    # With no entries read, a reflection was never offered.
    reflection_en = f" Reflection: {reflection}." if review.entry_count else ""
    reflection_ko = f" 회고: {reflection}." if review.entry_count else ""

    _print()
    _print(say(
        f"Review finished. To keep: {written} written, {later} for later, {rejected} rejected."
        f"{reflection_en}",
        f"리뷰를 마쳤습니다. 남길 것: 썼음 {written}건, 대기 {later}건, 남기지 않음 {rejected}건."
        f"{reflection_ko}",
    ))
    _print(f"-> {display_path(review.path)}")


def _work_through(review: Review, tool: Optional[str]) -> None:
    """Go through a review's items, saving after every choice."""
    _print(say(f"Review {review.name}: {review.start} to {review.end}", f"리뷰 {review.name}: {review.start} ~ {review.end}"))
    _print(say(
        f"{review.entry_count} entries on {review.active_days} days.",
        f"활동 {review.active_days}일, 기록 {review.entry_count}건입니다.",
    ))
    reflected = review.reflection == store.REFLECTION_OPEN and review.entry_count
    review = _reflect(review, tool)
    if review is None:
        return

    if review.proposals_pending and not _ask_for_proposals(review):
        return

    if not review.items:
        if reflected and review.reflection == store.REFLECTION_WRITTEN:
            if not _offer_when_nothing_to_keep(review):
                return
        else:
            _print()
            _print(say("Nothing in this period is worth keeping in a document.", "이 기간에는 문서로 남길 만한 내용이 없습니다."))

    if review.dropped:
        _print(say(
            f"{review.dropped} more candidates were left out. Their entries stay in the timeline.",
            f"이 밖의 후보 {review.dropped}건은 제외했습니다. 원본은 타임라인에 남아 있습니다.",
        ))

    if review.undecided_items():
        _print()
        _print(say(
            "To keep: for each, choose whether to write it now, later, or not at all.",
            "남길 것: 항목마다 지금 쓸지, 나중에 쓸지, 남기지 않을지 고르세요.",
        ))

    while True:
        waiting = review.undecided_items()
        if not waiting:
            break
        _show_item(review, waiting[0])
        if not _ask(_item_choices(review, waiting[0], tool)):
            return

    _finish(review)


def _emit_json(payload: dict) -> None:
    """Print one line of JSON. See ``json_output.emit``."""
    json_output.emit(payload)


def _json_failure(message: str, code: str = json_output.FAILED) -> NoReturn:
    json_output.fail(code, message)


def _review_as_json(since: Optional[str]) -> None:
    base = get_base_path()

    if not base.exists():
        _json_failure("Knowledge base not found. Run 'minit' first.", json_output.NOT_INITIALIZED)

    try:
        since_date = datetime.strptime(since, "%Y-%m-%d") if since else None
    except ValueError:
        _json_failure(f"Invalid date: {since}. Use YYYY-MM-DD.", json_output.INVALID_ARGUMENT)

    try:
        active = session.open_review(base, since=since_date)
        if active and active.proposals_pending:
            session.fill_proposals(base, active)
    except ReviewError as e:
        _json_failure(str(e), e.code)

    _emit_json({"ok": True, "review": store.review_to_dict(active) if active else None})


@review_app.command("add")
def add_item(
    title: str = typer.Argument(..., help="What to keep"),
    target: Optional[str] = typer.Option(None, "--target", help="Document to update. Without it, a new document"),
    doc_type: Optional[str] = typer.Option(None, "--type", help="Suggested document type: 참고, 이해, 방법, 판단"),
    why: str = typer.Option("", "--why", help="Why it is worth keeping"),
    evidence: Optional[List[str]] = typer.Option(None, "--evidence", help="A day whose entries it rests on (YYYY-MM-DD)"),
    heading: Optional[str] = typer.Option(None, "--heading", help="Heading to write under in the document, such as 열린 질문"),
    as_json: bool = typer.Option(False, "--json", help="Print the review as JSON"),
):
    """Add something to keep to the latest review.

    If that review has finished, the item waits for the next one.

    Examples:
        mreview add "Why the retry limit is 5" --why "A decision" --type 판단
        mreview add "Should long records be split?" --target news --heading "열린 질문"
    """
    from memory_tool.core.module import ModuleManager
    from memory_tool.review.proposer import add_split_notes
    from memory_tool.utils.module_docs import resolve_module_document

    def fail(message: str, code: str) -> None:
        if as_json:
            _json_failure(message, code)
        _fail(message)

    base = get_base_path()
    latest = store.latest_review(base)

    if latest is None:
        fail(say("There is no review yet. Run mreview first.", "아직 리뷰가 없습니다. 먼저 mreview를 실행해 주세요."), json_output.NOT_FOUND)
    if not title.strip():
        fail(say("What to keep is empty.", "남길 내용이 비어 있습니다."), json_output.INVALID_ARGUMENT)
    if heading and not target:
        fail(say("--heading needs --target.", "--heading은 --target과 함께 써야 합니다."), json_output.INVALID_ARGUMENT)
    if target and resolve_module_document(base / "modules" / target) is None:
        fail(say(f"Document not found: {target}", f"문서를 찾을 수 없습니다: {target}"), json_output.NOT_FOUND)

    item = store.add_item(
        latest, title.strip(), target=target, doc_type=doc_type,
        why=why, evidence=list(evidence or []), heading=heading,
    )
    add_split_notes(base, [item])
    store.save_review(latest)

    if as_json:
        _emit_json({"ok": True, "review": store.review_to_dict(latest)})
        return

    _print(say(f"Added item {item.number}: {item.title}", f"{item.number}번 항목을 추가했습니다: {item.title}"))
    if latest.is_done:
        _print(say("That review has finished, so it waits for the next one.", "끝난 리뷰이므로 다음 리뷰에서 묻습니다."))


@review_app.command("set")
def set_choice(
    number: int = typer.Argument(..., help="Item number"),
    choice: str = typer.Argument(..., help="write, later, reject or written"),
):
    """Choose for an item without being asked, printing the review as JSON.

    'write' only marks the item as being written. Starting the writing is up to
    the caller.
    """
    changes = {
        "write": store.start_writing,
        "later": store.defer,
        "reject": store.reject,
        "written": store.mark_written,
    }

    if choice not in changes:
        _json_failure(f"Unknown choice: {choice}. Choose from: {', '.join(changes)}", json_output.INVALID_ARGUMENT)

    try:
        latest = store.latest_review(get_base_path())
        if latest is None:
            _json_failure("There is no review yet.", json_output.NOT_FOUND)

        changes[choice](latest, number)
        store.finish_if_ready(latest)
        store.save_review(latest)
    except ReviewError as e:
        _json_failure(str(e), e.code)

    _emit_json({"ok": True, "review": store.review_to_dict(latest)})


@review_app.command("reflection")
def set_reflection(
    state: str = typer.Argument(..., help="written or skipped"),
):
    """Settle the reflection without being asked, printing the review as JSON."""
    if state not in (store.REFLECTION_WRITTEN, store.REFLECTION_SKIPPED):
        _json_failure(f"Unknown state: {state}. Choose written or skipped.", json_output.INVALID_ARGUMENT)

    try:
        latest = store.latest_review(get_base_path())
        if latest is None:
            _json_failure("There is no review yet.", json_output.NOT_FOUND)

        latest.reflection = state
        store.finish_if_ready(latest)
        store.save_review(latest)
    except ReviewError as e:
        _json_failure(str(e), e.code)

    _emit_json({"ok": True, "review": store.review_to_dict(latest)})


@review_app.callback()
def review(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, "--since", help="Start of the period (YYYY-MM-DD), for a new review"),
    with_tool: Optional[str] = typer.Option(None, "--with", help="How to write, skipping the menu: claude, codex, antigravity or solo"),
    as_json: bool = typer.Option(False, "--json", help="Start or read the review without asking anything, and print it as JSON"),
):
    """Reflect on the entries since the last review, and settle what to keep.

    Reflect with an AI CLI or on your own, or only see the AI's candidates. What
    is worth keeping then goes into documents, which you write yourself or with
    an AI. The reflection itself stays in the review file.

    With no command, starts a review of the entries since the last one, or
    continues the review in progress.

    Examples:
        mreview                       # Start or continue a review
        mreview --since 2026-10-01    # Start a review from a chosen date
        mreview list                  # Items waiting to be written
        mreview write 2               # Write item 2 now
        mreview write 2 --with codex  # The same, skipping the menu
        mreview done 2                # Mark item 2 as written
        mreview add "Topic" --why "Why"  # Add something to keep
    """
    if ctx.invoked_subcommand:
        return

    if as_json:
        _review_as_json(since)
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

        if (
            since_date and current and current.is_done
            and since_date > collector.parse_time(current.end)
        ):
            _print(say(
                f"Entries between {current.end} and {since} will not be reviewed: "
                "the next review starts where this one ends.",
                f"{current.end}부터 {since} 사이의 기록은 리뷰되지 않습니다. "
                "다음 리뷰는 이번 리뷰가 끝난 곳부터 시작합니다.",
            ))


        active = session.open_review(base, since=since_date, propose_now=False)

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
def list_items(
    as_json: bool = typer.Option(False, "--json", help="Print the items as JSON"),
):
    """Show the items waiting to be written."""
    try:
        latest = store.latest_review(get_base_path() if as_json else _base())
    except ReviewError as e:
        if as_json:
            _json_failure(str(e), e.code)
        _fail(str(e))

    waiting = latest.open_items() if latest else []

    if as_json:
        _emit_json({"ok": True, "items": [asdict(item) for item in waiting]})
        return

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
