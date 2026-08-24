"""Module templates (MOP v3.2): kinds, natures, and single-file assembly.

Modules are stored as one markdown file per module ([Folder]/[Folder].md), but
the templates are authored as separate documents -- module, current, decisions,
dependencies, interface -- because that is how they are reasoned about. This
module performs the assembly step so `mmodule create` produces a finished
document instead of a skeleton the user has to overwrite by hand.

Two classifications drive the result:

**Kind** answers "does the subject of this document already exist, and if so
what is its source of truth?"
  - ``knowledge``       -- it exists; the knowledge itself is the artifact
  - ``implementation``  -- it exists as code, and this is its summary
  - ``intent``          -- it does not exist yet; this is what I mean to do

Each Kind has one failure mode of its own, and the header fields exist to make
that failure visible: knowledge goes *wrong*, implementation goes *stale*, and
intent *drifts* -- it is neither decided nor dropped, and a provisional line
reads as settled a month later.

**Nature** answers "what makes this module need updating?" and selects the body
outline. ``knowledge`` and ``intent`` each have their own set;
``implementation`` has none.
  - knowledge/``concept``    understanding deepens    -> narrative
  - knowledge/``reference``  the subject is patched   -> lookup tables
  - knowledge/``analysis``   new evidence appears     -> argument + red team
  - knowledge/``tracker``    time passes              -> snapshots + prediction log
  - knowledge/``method``     application feedback     -> procedure + failure modes
  - intent/``idea``          a new association lands  -> divergent
  - intent/``inquiry``       a round of debate ends   -> convergent
  - intent/``plan``          reality contradicts it   -> executable

Templates are resolved project-first: a project that keeps its own copies under
``<base>/templates/<kind>/`` uses those, so local edits are never overwritten by
the bundled defaults.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

KINDS = ("knowledge", "implementation", "intent")

#: Natures per kind. A nature name belongs to exactly one kind, so a bare
#: --nature is enough to infer the kind (see `kind_for_nature`).
KIND_NATURES: Dict[str, Tuple[str, ...]] = {
    "knowledge": ("concept", "reference", "analysis", "tracker", "method"),
    "implementation": (),
    "intent": ("idea", "inquiry", "plan"),
}

#: Every nature, in kind order. Used where the owning kind is not yet known --
#: parsing a natures menu, for instance.
NATURES = tuple(n for natures in KIND_NATURES.values() for n in natures)

#: Kinds that carry a Nature at all.
NATURE_KINDS = tuple(k for k, natures in KIND_NATURES.items() if natures)

#: Kept for callers that predate `intent`: the kind a bare --nature used to mean.
NATURE_KIND = "knowledge"

#: One-line descriptions, used in CLI help and error messages.
KIND_SUMMARY = {
    "knowledge": "the knowledge itself is the artifact (concepts, references, analysis)",
    "implementation": "code is the source of truth and this module summarizes it",
    "intent": "it does not exist yet -- ideas, open questions, and plans",
}

NATURE_SUMMARY = {
    "concept": "understanding deepens -- narrative: problem, analogy, principle, example",
    "reference": "the subject gets patched -- lookup tables, formulas, sources, versions",
    "analysis": "new evidence appears -- facts, interpretation, red team, impact",
    "tracker": "time passes -- snapshots, scenarios, calendar, prediction log",
    "method": "application feedback -- premises, procedure, checklist, failure modes",
    "idea": "a new association lands -- diverge: seed, stimulus, value hypothesis",
    "inquiry": "a round of debate ends -- converge: criteria first, then options",
    "plan": "reality contradicts the plan -- done-definition, phases, rollback",
}


def natures_for(kind: str) -> Tuple[str, ...]:
    """Natures available for a kind, empty if it carries none."""
    return KIND_NATURES.get(kind, ())


def kind_for_nature(nature: str) -> Optional[str]:
    """The kind a nature belongs to, or None if the name is unknown.

    Nature names do not overlap across kinds, so `--nature plan` alone is an
    unambiguous request for an intent module.
    """
    for kind, natures in KIND_NATURES.items():
        if nature in natures:
            return kind
    return None

#: Order in which template documents are concatenated into the single file.
#:
#: "module" is deliberately thin -- a title, the classification fields and a
#: one-line purpose -- and "scope" carries the rest of the metadata at the end.
#: With everything in one block up top, the first line of actual content landed
#: on line 48 or later, so the part of the document that is read most often was
#: the part you had to scroll past boundary declarations to reach.
ASSEMBLY_ORDER = (
    "module",
    "current",
    "decisions",
    "dependencies",
    "interface",
    "scope",
)

#: Files required for a directory to count as a usable template set.
REQUIRED_FILES = ("module.md", "current.md")

SECTION_SEPARATOR = "\n\n---\n\n"


#: Parts that must be present however the template is stored.
REQUIRED_PARTS = ("module", "current")

#: Single-file templates keep every part in one document, marked by comments:
#:
#:     <!-- part: module -->
#:     ...
#:     ---
#:     <!-- part: current -->
#:
#: Markers rather than positional splitting: a "---" inside a section (a table
#: rule, a nested example) would silently shift every following part by one, and
#: the result would still look like a valid document.
PART_MARKER = re.compile(r"^<!--\s*part:\s*([a-z]+)\s*-->[ \t]*$", re.MULTILINE)

#: The natures part is a menu to choose from, never emitted into a module.
NATURES_PART = "natures"

#: The draft part is a whole seed document, emitted instead of the assembly.
#:
#: A module is not born finished. The full skeleton asks for a confidence
#: rating, a scope boundary and a citable conclusion before a single line of
#: content exists, which is a lot to answer about something you have just
#: started thinking about. The draft is what you can honestly fill in on day
#: one, and it ends with the ladder of what to add next.
DRAFT_PART = "draft"

#: Every part a template file may define.
ALL_PARTS = (*ASSEMBLY_ORDER, NATURES_PART, DRAFT_PART)

def single_file_name(kind: str) -> str:
    """Filename of a single-file template for a kind."""
    return f"{kind}.md"


class TemplateError(Exception):
    """Raised when templates are missing or unusable."""


@dataclass
class TemplateChoice:
    """A validated kind/nature selection."""

    kind: str
    nature: Optional[str] = None

    def __post_init__(self):
        if self.kind not in KINDS:
            raise TemplateError(
                f"Unknown module kind: '{self.kind}'. "
                f"Choose one of: {', '.join(KINDS)}"
            )

        if self.nature is not None:
            allowed = natures_for(self.kind)
            if not allowed:
                raise TemplateError(
                    f"--nature applies only to "
                    f"{' and '.join(NATURE_KINDS)} modules, not '{self.kind}'."
                )
            if self.nature not in allowed:
                owner = kind_for_nature(self.nature)
                hint = (
                    f" ('{self.nature}' belongs to '{owner}'.)"
                    if owner
                    else ""
                )
                raise TemplateError(
                    f"Unknown nature for '{self.kind}': '{self.nature}'. "
                    f"Choose one of: {', '.join(allowed)}.{hint}"
                )


def bundled_templates_root() -> Path:
    """Directory of templates shipped with memory_tool."""
    return Path(__file__).parent.parent / "templates" / "modules"


def _is_usable(directory: Path) -> bool:
    """True if `directory` holds at least the required template files."""
    return directory.is_dir() and all(
        (directory / name).is_file() for name in REQUIRED_FILES
    )


def resolve_template_dir(kind: str, memory_path: Optional[Path] = None) -> Path:
    """Find the template directory for a kind.

    A project's own ``<base>/templates/<kind>/`` wins over the bundled copies,
    so customizations survive upgrades and are not silently ignored.

    Args:
        kind: "knowledge" or "implementation"
        memory_path: The project's base folder, if known

    Returns:
        Directory containing the template documents.

    Raises:
        TemplateError: If no usable template directory exists.
    """
    candidates: List[Path] = []
    if memory_path is not None:
        candidates.append(Path(memory_path) / "templates" / kind)
    candidates.append(bundled_templates_root() / kind)

    for candidate in candidates:
        if _is_usable(candidate):
            return candidate

    raise TemplateError(
        f"No usable '{kind}' template found. Looked in: "
        + ", ".join(str(c) for c in candidates)
        + f" (each needs {' and '.join(REQUIRED_FILES)})"
    )


def _parse_natures(
    content: str, natures: Optional[Tuple[str, ...]] = None
) -> Dict[str, str]:
    """Parse the natures menu into {nature: body outline}.

    Each nature is documented as a ``## <nature> (...)`` heading followed by a
    fenced block holding the outline to paste into the body section.

    Args:
        content: The natures markdown, from natures.md or the natures part
        natures: Names to look for; defaults to every known nature. Passing the
            kind's own set keeps a heading that happens to share a nature name
            from being picked up as a menu entry.

    Returns:
        Mapping of nature name to its outline markdown (may be empty).
    """
    if not content:
        return {}

    names = natures if natures else NATURES
    blocks: Dict[str, str] = {}

    # "## concept (개념) — 서사형" ... then the first fenced block after it.
    heading = re.compile(r"^##\s+(" + "|".join(names) + r")\b", re.MULTILINE)
    matches = list(heading.finditer(content))

    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = content[start:end]

        fence = re.search(r"```[a-zA-Z]*\n(.*?)```", section, re.DOTALL)
        if not fence:
            continue

        body = fence.group(1).strip("\n")

        # The outline may repeat the "## 2. 본문" heading it is meant to fill.
        # Drop that line so the assembled document has exactly one such heading
        # (one authored copy carries a stray suffix, which this also removes).
        lines = body.split("\n")
        if lines and re.match(r"^##\s*2\.", lines[0]):
            lines = lines[1:]
            body = "\n".join(lines).strip("\n")

        blocks[name] = body

    return blocks


#: Matches the body section heading and everything up to the next H2.
_BODY_SECTION = re.compile(
    r"(^##\s*2\.[^\n]*\n)(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _splice_nature(current_md: str, nature_body: str) -> str:
    """Replace the body section of current.md with a nature's outline.

    Args:
        current_md: Contents of the knowledge current.md template
        nature_body: Outline to insert

    Returns:
        current.md with its body section filled in.
    """
    if not nature_body:
        return current_md

    # "\1" keeps the heading line (including its newline); the extra "\n" is the
    # blank line Markdown needs between a heading and the content below it.
    replacement = "\\1\n" + nature_body.replace("\\", r"\\") + "\n\n"
    spliced, count = _BODY_SECTION.subn(replacement, current_md, count=1)

    if count:
        return spliced

    # No body heading to fill (a customized template may omit it): append rather
    # than discard the outline.
    return current_md.rstrip("\n") + "\n\n## 2. 본문\n\n" + nature_body + "\n"


def _fill_field(text: str, token: str, value: str) -> str:
    """Replace a ``[placeholder]`` without touching ``[[wiki links]]``.

    The placeholders and the wiki-link syntax share the bracket, so a plain
    replace turns the ``[[모듈명]]`` in a Dependencies example into ``[name]`` --
    no longer a link, and no longer visibly a placeholder either. The doubled
    brackets are what tells the two apart.

    Args:
        text: Template text
        token: The placeholder, brackets included
        value: What to put in its place

    Returns:
        Text with single-bracket occurrences filled in.
    """
    pattern = re.compile(r"(?<!\[)" + re.escape(token) + r"(?!\])")
    return pattern.sub(lambda _: value, text)


def _apply_placeholders(
    text: str,
    name: str,
    choice: TemplateChoice,
    description: str,
    tags: str,
    today: str,
) -> str:
    """Fill in the template placeholders.

    Args:
        text: Template text
        name: Module name or path
        choice: Validated kind/nature
        description: Purpose text
        tags: Comma-separated tags
        today: ISO date string

    Returns:
        Text with placeholders replaced.
    """
    basename = Path(name).name

    # Dates: every occurrence is a field to fill, not a format hint.
    text = text.replace("YYYY-MM-DD", today)

    # Titles. The path form is used by implementation templates, the plain name
    # by knowledge ones.
    text = _fill_field(text, "[경로]", name)
    text = _fill_field(text, "[모듈명]", basename)
    text = _fill_field(text, "[주제]", basename)
    text = _fill_field(text, "[모듈]", basename)

    # Collapse the Kind/Nature option lists down to the actual selection.
    text = _set_kind_field(text, choice)

    if tags:
        # Match only trailing spaces, not the newline: \s* would swallow the
        # blank line that separates the header block from the first section.
        text = re.sub(
            r"^\*\*Tags:\*\*[ \t]*$",
            f"**Tags:** {tags}",
            text,
            count=1,
            flags=re.MULTILINE,
        )

    if description:
        text = _fill_purpose(text, description)

    return text


def _set_kind_field(text: str, choice: TemplateChoice) -> str:
    """Replace the Kind/Nature options on the header line with the selection.

    The header line mixes fields, for example::

        **Kind:** implementation | **Role:** leaf | root

    Both the field values and the line itself are pipe-separated, so a plain
    regex either stops too early or swallows neighbouring fields. Splitting the
    line into fields and rewriting only Kind and Nature keeps everything else
    (``Role``, ``Status``) exactly as authored.

    Args:
        text: Template text
        choice: Validated kind/nature

    Returns:
        Text with the Kind (and Nature) fields set.
    """
    lines = text.split("\n")

    for index, line in enumerate(lines):
        if not line.startswith("**Kind:**"):
            continue

        rebuilt: List[str] = [f"**Kind:** {choice.kind}"]
        if choice.nature:
            rebuilt.append(f"**Nature:** {choice.nature}")

        # Split only at pipes that begin a new field, so a field's own
        # option list ("**Role:** leaf | root") stays intact.
        for segment in re.split(r"\|\s*(?=\*\*)", line):
            stripped = segment.strip()
            if stripped.startswith("**Kind:**") or stripped.startswith("**Nature:**"):
                continue
            if stripped:
                rebuilt.append(stripped)

        lines[index] = " | ".join(rebuilt)
        break

    return "\n".join(lines)


def _fill_purpose(text: str, description: str) -> str:
    """Insert the description under the purpose heading.

    The heading is followed by an instructional comment; the description goes
    after it so the guidance stays visible for later editing.

    A draft has no "목적과 목표" heading -- it opens straight into "지금 아는
    것" or "하려는 것" -- so the first section stands in for it. Without that
    fallback a --desc passed alongside --draft was accepted and then silently
    dropped, which is worse than refusing it.
    """
    # The heading group is [^\n]*, not .* -- DOTALL applies to the whole pattern,
    # so a dot there runs past the heading and swallows the document down to its
    # last newline, putting the description at the very end of the file.
    patterns = (
        re.compile(
            r"(^##[ \t]*목적과 목표[ \t]*\n)(.*?)(?=^##\s|\Z)",
            re.MULTILINE | re.DOTALL,
        ),
        re.compile(
            r"(^##[ \t]+\S[^\n]*\n)(.*?)(?=^##\s|\Z)",
            re.MULTILINE | re.DOTALL,
        ),
    )

    def repl(match: re.Match) -> str:
        head, body = match.group(1), match.group(2)
        return f"{head}{body.rstrip()}\n\n{description}\n\n"

    for pattern in patterns:
        filled, count = pattern.subn(repl, text, count=1)
        if count:
            return filled

    return text


def parse_single_file_template(text: str) -> Dict[str, str]:
    """Split a single-file template into its parts.

    Args:
        text: Whole template document

    Returns:
        Mapping of part name to its markdown, in document order. Text before the
        first marker is ignored, so a file may carry a header comment.
    """
    parts: Dict[str, str] = {}
    matches = list(PART_MARKER.finditer(text))

    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]

        # A "---" immediately before the next marker is the separator between
        # sections, not content belonging to this one.
        body = re.sub(r"\n+-{3,}\s*$", "", body.rstrip())
        parts[name] = body.strip("\n")

    return parts


def merge_template_dir(directory: Path) -> str:
    """Render a directory template set as one single-file template.

    Args:
        directory: A templates/<kind>/ folder

    Returns:
        The merged document, ready to write as templates/<kind>.md.

    Raises:
        TemplateError: If the required parts are missing.
    """
    missing = [n for n in REQUIRED_PARTS if not (directory / f"{n}.md").is_file()]
    if missing:
        raise TemplateError(
            f"Cannot merge {directory}: missing "
            + ", ".join(f"{n}.md" for n in missing)
        )

    chunks: List[str] = [
        "<!-- Single-file module template.",
        "     Each part below becomes one section of the assembled module,",
        "     joined in this order and separated by a horizontal rule.",
        f"     Parts: {', '.join(ASSEMBLY_ORDER)}",
        "     The 'natures' part is a menu: one outline is spliced into the",
        "     body of 'current' and the rest are never emitted.",
        "     The 'draft' part is the seed document emitted by --draft, on its own. -->",
        "",
    ]

    body: List[str] = []

    for part in ALL_PARTS:
        path = directory / f"{part}.md"
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8").strip("\n")
        body.append(f"<!-- part: {part} -->\n\n{content}")

    return "\n".join(chunks) + SECTION_SEPARATOR.join(body) + "\n"


def load_template_parts(
    kind: str, memory_path: Optional[Path] = None
) -> Tuple[Dict[str, str], Path]:
    """Load a kind's template parts from whichever storage form exists.

    Single-file templates win over directories at the same level, and a
    project's own templates win over the bundled ones, so a customization is
    never silently ignored.

    Args:
        kind: "knowledge" or "implementation"
        memory_path: The project's base folder, if known

    Returns:
        (parts, origin path) -- origin is used in error messages.

    Raises:
        TemplateError: If no usable template exists.
    """
    roots: List[Path] = []
    if memory_path is not None:
        roots.append(Path(memory_path) / "templates")
    roots.append(bundled_templates_root())

    tried: List[Path] = []

    for root in roots:
        single = root / single_file_name(kind)
        tried.append(single)
        if single.is_file():
            try:
                parts = parse_single_file_template(single.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as e:
                raise TemplateError(f"Could not read {single}: {e}") from e

            missing = [n for n in REQUIRED_PARTS if n not in parts]
            if missing:
                raise TemplateError(
                    f"{single} is missing required part(s): "
                    + ", ".join(f"<!-- part: {n} -->" for n in missing)
                )
            return parts, single

        directory = root / kind
        tried.append(directory)
        if _is_usable(directory):
            parts = {}
            for part in ALL_PARTS:
                path = directory / f"{part}.md"
                if path.is_file():
                    try:
                        parts[part] = path.read_text(encoding="utf-8").strip("\n")
                    except (OSError, UnicodeDecodeError) as e:
                        raise TemplateError(f"Could not read {path}: {e}") from e
            return parts, directory

    raise TemplateError(
        f"No usable '{kind}' template found. Looked for: "
        + ", ".join(str(t) for t in tried)
    )


def build_module_document(
    name: str,
    kind: str,
    nature: Optional[str] = None,
    description: str = "",
    tags: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
    draft: bool = False,
) -> str:
    """Assemble a single-file module document from templates.

    Args:
        name: Module name or path (e.g. "AI/basics")
        kind: "knowledge", "implementation" or "intent"
        nature: Body outline for knowledge and intent modules
        description: Purpose text
        tags: Module tags
        memory_path: Base folder, so project templates take precedence
        draft: Emit the seed document instead of the full skeleton. The
            classification still applies -- a draft is the same kind of module
            at an earlier point, not a different kind -- so the header carries
            the chosen Kind and Nature either way.

    Returns:
        The complete markdown document.

    Raises:
        TemplateError: If the kind/nature is invalid or templates are missing.
    """
    choice = TemplateChoice(kind=kind, nature=nature)
    parts, origin = load_template_parts(choice.kind, memory_path)

    today = datetime.now().strftime("%Y-%m-%d")
    tags_str = ", ".join(tags) if tags else ""

    if draft:
        seed = parts.get(DRAFT_PART)
        if seed is None:
            raise TemplateError(
                f"{origin} has no '<!-- part: {DRAFT_PART} -->' section, so "
                f"--draft has nothing to emit for '{choice.kind}'."
            )
        return (
            _apply_placeholders(
                seed,
                name=name,
                choice=choice,
                description=description,
                tags=tags_str,
                today=today,
            ).strip("\n")
            + "\n"
        )

    natures = (
        _parse_natures(parts.get(NATURES_PART, ""), natures_for(choice.kind))
        if choice.nature
        else {}
    )
    if choice.nature and choice.nature not in natures:
        raise TemplateError(
            f"Nature '{choice.nature}' is not defined in {origin}."
        )

    sections: List[str] = []

    for part in ASSEMBLY_ORDER:
        content = parts.get(part)
        if content is None:
            # decisions/dependencies/interface are optional in a custom set.
            if part in REQUIRED_PARTS:
                raise TemplateError(f"Required template part missing in {origin}: {part}")
            continue

        if part == "current" and choice.nature:
            content = _splice_nature(content, natures[choice.nature])

        content = _apply_placeholders(
            content,
            name=name,
            choice=choice,
            description=description,
            tags=tags_str,
            today=today,
        )

        sections.append(content.strip("\n"))

    return SECTION_SEPARATOR.join(sections) + "\n"


#: Top-level headings, which is how a part is recognized as already present.
_H1 = re.compile(r"^#\s+(\S.*?)\s*$")


def _h1_titles(text: str) -> List[str]:
    """Top-level headings of a document, ignoring fenced blocks.

    A template's own examples quote whole markdown files, headings included, so
    a naive scan would report sections the document does not actually have.
    """
    titles: List[str] = []
    in_fence = False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _H1.match(line)
        if match:
            titles.append(match.group(1))

    return titles


def grow_module_document(
    existing: str,
    name: str,
    kind: str,
    nature: Optional[str] = None,
    memory_path: Optional[Path] = None,
) -> Tuple[str, List[str]]:
    """Append the skeleton sections a document does not have yet.

    This is the second half of the draft workflow. The seed holds what you can
    honestly write on day one; when a module outgrows it, the remaining sections
    are appended rather than the author copying them out of the template by
    hand. What is already written is never touched: a section counts as present
    when its top-level heading is, so nothing is duplicated and nothing is
    overwritten.

    Args:
        existing: The current document
        name: Module name or path, for placeholder substitution
        kind: The module's kind
        nature: Body outline, if the kind takes one
        memory_path: Base folder, so project templates take precedence

    Returns:
        (grown document, names of the parts appended). The parts list is empty
        when the document already has every section, and the document comes
        back unchanged in that case.

    Raises:
        TemplateError: If the kind/nature is invalid or templates are missing.
    """
    choice = TemplateChoice(kind=kind, nature=nature)
    parts, origin = load_template_parts(choice.kind, memory_path)

    today = datetime.now().strftime("%Y-%m-%d")

    natures = (
        _parse_natures(parts.get(NATURES_PART, ""), natures_for(choice.kind))
        if choice.nature
        else {}
    )
    if choice.nature and choice.nature not in natures:
        raise TemplateError(f"Nature '{choice.nature}' is not defined in {origin}.")

    present = set(_h1_titles(existing))
    sections: List[str] = []
    added: List[str] = []

    for part in ASSEMBLY_ORDER:
        content = parts.get(part)
        if content is None:
            continue

        if part == "current" and choice.nature:
            content = _splice_nature(content, natures[choice.nature])

        # Tags and description are left alone: the draft already carries them,
        # and this call must not overwrite what the author wrote.
        content = _apply_placeholders(
            content,
            name=name,
            choice=choice,
            description="",
            tags="",
            today=today,
        )

        titles = _h1_titles(content)
        if titles and titles[0] in present:
            continue

        sections.append(content.strip("\n"))
        added.append(part)

    if not sections:
        return existing, []

    grown = existing.rstrip("\n") + SECTION_SEPARATOR + SECTION_SEPARATOR.join(sections)
    return grown + "\n", added


def describe_choices() -> str:
    """Render the available kinds and natures for CLI help."""
    lines = ["Kinds:"]
    for kind in KINDS:
        lines.append(f"  {kind:<16} {KIND_SUMMARY[kind]}")

    for kind in NATURE_KINDS:
        lines.append("")
        lines.append(f"Natures ({kind}):")
        for nature in natures_for(kind):
            lines.append(f"  {nature:<16} {NATURE_SUMMARY[nature]}")

    return "\n".join(lines)
