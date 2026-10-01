"""Locate and rewrite sections of a single-document module.

A consolidated module keeps what used to be decisions.md and current.md as
top-level sections of one file, so archiving works on a slice of the document
rather than on a whole file. Everything here is line-based and leaves any text
it does not recognize exactly where it was: an archive that guesses wrong must
not cost the author a paragraph.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

#: A horizontal rule in any of the spellings found in real modules: "---",
#: "***", and the em-dash or box-drawing lines that some editors substitute.
RULE = re.compile(r"^\s*([-—─_*=])(?:\s*\1){2,}\s*$")

#: Headings that open a decision entry and carry its number.
#:   ## Decision 3: Title (2026-08-25)
#:   ### #37: Title (2025-11-20)
#:   ## 결정 #4: Title
#:   ### #35b: Title     -- a letter splits one number into ordered entries
ENTRY_NUMBER = re.compile(
    r"(?:\bDecision\s+#?|결정\s*#\s*|결정\s+|^#)(\d+)([a-z]?)(?![0-9a-z])",
    re.IGNORECASE,
)

#: The older entry form: the heading is the date, the number is in the body.
#:   ### 2025-11-14: Title
#:   **결정 #12:** ...
LEGACY_ENTRY = re.compile(r"^\d{4}-\d{2}-\d{2}:")
BODY_NUMBER = re.compile(r"\*\*결정 #(\d+):")

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

DECISIONS_TITLE = re.compile(r"decisions|결정", re.IGNORECASE)
CURRENT_TITLE = re.compile(r"^current\b", re.IGNORECASE)
RELATED_FILES_TITLE = re.compile(r"related files", re.IGNORECASE)


class SectionError(Exception):
    """The document does not have the section in a form that can be edited."""


@dataclass
class Heading:
    index: int
    level: int
    title: str


@dataclass
class Entry:
    """One decision: its heading line, its body, and what follows it."""

    number: int
    #: The letter after the number in "#35b", lowercased; empty if none.
    suffix: str
    date: Optional[str]
    title: str
    header: str
    #: Body lines after the heading, trailing blanks and rules removed.
    body: List[str]
    #: The blank and rule lines between this entry and the next thing.
    gap: List[str] = field(default_factory=list)

    @property
    def content(self) -> str:
        # Not stripped: the archive should read exactly as the module did.
        return "\n".join(self.body)

    @property
    def label(self) -> str:
        return f"{self.number}{self.suffix}"


def read_document(path: Path) -> Tuple[List[str], str]:
    """Read a document as lines, remembering its line ending."""
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n").split("\n"), newline


def write_document(path: Path, lines: List[str], newline: str) -> None:
    """Write lines back with the line ending the document already used."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(newline.join(lines))


def scan_headings(lines: List[str], start: int = 0, stop: Optional[int] = None) -> List[Heading]:
    """Headings between two line indexes, ignoring fenced blocks.

    Module documents quote whole markdown files and shell sessions inside
    fences, and a "# comment" there is content, not structure.
    """
    stop = len(lines) if stop is None else stop
    found: List[Heading] = []
    in_fence = False

    for index in range(start, stop):
        line = lines[index]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if match:
            found.append(Heading(index, len(match.group(1)), match.group(2)))

    return found


def find_section(
    lines: List[str], matches: Callable[[str], bool], label: str
) -> Tuple[int, int]:
    """Find the one top-level section whose title satisfies ``matches``.

    Returns:
        (index of the H1 line, index of the next H1 or the end of the document)

    Raises:
        SectionError: If there is no such section, or more than one. A document
            that merged several modules has several, and picking one would
            silently archive the wrong module's history.
    """
    tops = [h for h in scan_headings(lines) if h.level == 1]
    hits = [i for i, h in enumerate(tops) if matches(h.title)]

    if not hits:
        raise SectionError(f"No '# ...' {label} section found")

    if len(hits) > 1:
        where = ", ".join(f"line {tops[i].index + 1} '{tops[i].title}'" for i in hits)
        raise SectionError(
            f"{len(hits)} {label} sections found ({where}). "
            f"Split the document so each module has one."
        )

    position = hits[0]
    end = tops[position + 1].index if position + 1 < len(tops) else len(lines)
    return tops[position].index, end


def _split_trailing(lines: List[str]) -> Tuple[List[str], List[str]]:
    """Separate trailing blank and rule lines from the text before them."""
    cut = len(lines)
    while cut > 0 and (not lines[cut - 1].strip() or RULE.match(lines[cut - 1])):
        cut -= 1
    return lines[:cut], lines[cut:]


def _entry_number(heading: Heading, body: List[str]) -> Optional[Tuple[int, str]]:
    """(number, suffix) of a decision heading, or None if it is not one."""
    match = ENTRY_NUMBER.search(heading.title)
    if match:
        return int(match.group(1)), match.group(2).lower()

    if LEGACY_ENTRY.match(heading.title):
        found = BODY_NUMBER.search("\n".join(body))
        if found:
            return int(found.group(1)), ""

    return None


def _body_end(lines: List[str], heading: Heading, later: List[Heading], stop: int) -> int:
    for other in later:
        if other.level <= heading.level:
            return other.index
    return stop


@dataclass
class DecisionsSection:
    """The decisions section of a document, cut into its parts.

    Reassembling ``head + preamble + entries (with gaps) + tail`` reproduces the
    original lines exactly, which is what lets a rewrite touch only the entries
    that were archived.
    """

    lines: List[str]
    start: int
    end: int
    preamble: List[str]
    entries: List[Entry]
    tail: List[str]

    @classmethod
    def parse(cls, lines: List[str]) -> "DecisionsSection":
        start, end = find_section(
            lines, lambda t: bool(DECISIONS_TITLE.search(t)), "decisions"
        )
        headings = scan_headings(lines, start + 1, end)

        # The first numbered heading sets the entry level. Headings above it
        # ("## Recent Decisions") are framing and stay in the preamble.
        entry_level = None
        for position, heading in enumerate(headings):
            stop = _body_end(lines, heading, headings[position + 1:], end)
            if _entry_number(heading, lines[heading.index + 1:stop]) is not None:
                entry_level = heading.level
                first = position
                break

        if entry_level is None:
            return cls(lines, start, end, lines[start + 1:end], [], [])

        # Once entries begin, the first heading at their level that is not an
        # entry ends them: "## Dependencies" placed under the decisions H1.
        starts: List[Heading] = []
        tail_start = end
        for position in range(first, len(headings)):
            heading = headings[position]
            if heading.level > entry_level:
                continue
            stop = _body_end(lines, heading, headings[position + 1:], end)
            if _entry_number(heading, lines[heading.index + 1:stop]) is None:
                tail_start = heading.index
                break
            starts.append(heading)

        entries: List[Entry] = []
        for position, heading in enumerate(starts):
            stop = starts[position + 1].index if position + 1 < len(starts) else tail_start
            raw_body = lines[heading.index + 1:stop]
            body, gap = _split_trailing(raw_body)
            date = DATE.search(heading.title)
            number, suffix = _entry_number(heading, raw_body)
            entries.append(
                Entry(
                    number=number,
                    suffix=suffix,
                    date=date.group(0) if date else None,
                    title=heading.title,
                    header=lines[heading.index],
                    body=body,
                    gap=gap,
                )
            )

        return cls(
            lines,
            start,
            end,
            preamble=lines[start + 1:starts[0].index],
            entries=entries,
            tail=lines[tail_start:end],
        )

    def rewrite(self, keep: List[Entry], note: str) -> List[str]:
        """The whole document with only ``keep`` left in the section.

        Kept entries stay in their original order. The note goes directly
        under the section title, where the next reader looks first.
        """
        kept_ids = {id(e) for e in keep}
        remaining = [e for e in self.entries if id(e) in kept_ids]

        # Entries were separated by whatever the author used between the first
        # two; reuse it so the rewritten section still looks like theirs.
        separator = self.entries[0].gap if len(self.entries) > 1 else [""]
        closing = self.entries[-1].gap if self.entries else []

        out = [self.lines[self.start], "", note]
        preamble = self.preamble
        if preamble and preamble[0].strip():
            out.append("")

        if remaining:
            out += preamble
            for position, entry in enumerate(remaining):
                if position:
                    out += separator
                out += [entry.header] + entry.body
            out += closing
        else:
            body, _ = _split_trailing(preamble)
            out += body + (closing or [""])

        out += self.tail
        return self.lines[: self.start] + out + self.lines[self.end:]


@dataclass
class CurrentSection:
    """The current-status section: its lines and the separator after it."""

    lines: List[str]
    start: int
    end: int
    body: List[str]
    gap: List[str]

    @classmethod
    def parse(cls, lines: List[str]) -> "CurrentSection":
        start, end = find_section(
            lines, lambda t: bool(CURRENT_TITLE.search(t)), "current status"
        )
        body, gap = _split_trailing(lines[start:end])
        return cls(lines, start, end, body, gap)

    def related_files(self) -> List[str]:
        """The Related Files block, which must survive a reset.

        It is the module's anchor to the code and what mcheck validates;
        resetting it along with the status would leave the module unanchored.
        """
        stop = self.start + len(self.body)
        headings = scan_headings(self.lines, self.start + 1, stop)

        for position, heading in enumerate(headings):
            if RELATED_FILES_TITLE.search(heading.title):
                block_end = _body_end(self.lines, heading, headings[position + 1:], stop)
                block, _ = _split_trailing(self.lines[heading.index:block_end])
                return block

        return []

    def rewrite(self, phase: int, archive_link: str) -> List[str]:
        """The document with this section reset to an empty status."""
        out = [
            self.lines[self.start],
            "",
            f"> **Phase {phase + 1} in progress**",
            "",
            f"For Phase {phase} status, see {archive_link}",
            "",
            "## Active Work",
            "",
            "### In Progress",
            "-",
            "",
            "### Next Steps",
            "-",
        ]

        related = self.related_files()
        if related:
            out += [""] + related

        out += self.gap or [""]
        return self.lines[: self.start] + out + self.lines[self.end:]
