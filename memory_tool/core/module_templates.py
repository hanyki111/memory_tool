"""Module templates (MOP v3.2): kinds, natures, and single-file assembly.

Modules are stored as one markdown file per module ([Folder]/[Folder].md), but
the templates are authored as separate documents -- module, current, decisions,
dependencies, interface -- because that is how they are reasoned about. This
module performs the assembly step so `mmodule create` produces a finished
document instead of a skeleton the user has to overwrite by hand.

Two classifications drive the result:

**Kind** answers "when this document is wrong, is the *knowledge* wrong or just
the *document*?"
  - ``knowledge``       -- the knowledge itself is the artifact
  - ``implementation``  -- code is the source of truth, this is its summary

**Nature** (``knowledge`` only) answers "what makes this module need updating?"
and selects the body outline:
  - ``concept``    understanding deepens      -> narrative
  - ``reference``  the subject is patched     -> lookup tables
  - ``analysis``   new evidence appears       -> argument + red team
  - ``tracker``    time passes                -> snapshots + prediction log
  - ``method``     application feedback       -> procedure + failure modes

Templates are resolved project-first: a project that keeps its own copies under
``<base>/templates/<kind>/`` uses those, so local edits are never overwritten by
the bundled defaults.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

KINDS = ("knowledge", "implementation")
NATURES = ("concept", "reference", "analysis", "tracker", "method")

#: Only knowledge modules carry a Nature; implementation modules do not.
NATURE_KIND = "knowledge"

#: One-line descriptions, used in CLI help and error messages.
KIND_SUMMARY = {
    "knowledge": "the knowledge itself is the artifact (concepts, references, analysis)",
    "implementation": "code is the source of truth and this module summarizes it",
}

NATURE_SUMMARY = {
    "concept": "understanding deepens -- narrative: problem, analogy, principle, example",
    "reference": "the subject gets patched -- lookup tables, formulas, sources, versions",
    "analysis": "new evidence appears -- facts, interpretation, red team, impact",
    "tracker": "time passes -- snapshots, scenarios, calendar, prediction log",
    "method": "application feedback -- premises, procedure, checklist, failure modes",
}

#: Order in which template documents are concatenated into the single file.
ASSEMBLY_ORDER = ("module", "current", "decisions", "dependencies", "interface")

#: Files required for a directory to count as a usable template set.
REQUIRED_FILES = ("module.md", "current.md")

SECTION_SEPARATOR = "\n\n---\n\n"


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
            if self.kind != NATURE_KIND:
                raise TemplateError(
                    f"--nature applies only to '{NATURE_KIND}' modules, "
                    f"not '{self.kind}'."
                )
            if self.nature not in NATURES:
                raise TemplateError(
                    f"Unknown nature: '{self.nature}'. "
                    f"Choose one of: {', '.join(NATURES)}"
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


def _read_natures(template_dir: Path) -> Dict[str, str]:
    """Parse natures.md into {nature: body outline}.

    Each nature is documented as a ``## <nature> (...)`` heading followed by a
    fenced block holding the outline to paste into the body section.

    Args:
        template_dir: Directory that may contain natures.md

    Returns:
        Mapping of nature name to its outline markdown (may be empty).
    """
    natures_file = template_dir / "natures.md"
    if not natures_file.is_file():
        return {}

    try:
        content = natures_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    blocks: Dict[str, str] = {}

    # "## concept (개념) — 서사형" ... then the first fenced block after it.
    heading = re.compile(r"^##\s+(" + "|".join(NATURES) + r")\b", re.MULTILINE)
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
    text = text.replace("[경로]", name)
    text = text.replace("[모듈명]", basename)
    text = text.replace("[주제]", basename)
    text = text.replace("[모듈]", basename)

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
    """
    pattern = re.compile(r"(^##\s*목적과 목표\s*\n)(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)

    def repl(match: re.Match) -> str:
        head, body = match.group(1), match.group(2)
        return f"{head}{body.rstrip()}\n\n{description}\n\n"

    filled, count = pattern.subn(repl, text, count=1)
    return filled if count else text


def build_module_document(
    name: str,
    kind: str,
    nature: Optional[str] = None,
    description: str = "",
    tags: Optional[List[str]] = None,
    memory_path: Optional[Path] = None,
) -> str:
    """Assemble a single-file module document from templates.

    Args:
        name: Module name or path (e.g. "AI/basics")
        kind: "knowledge" or "implementation"
        nature: Body outline for knowledge modules
        description: Purpose text
        tags: Module tags
        memory_path: Base folder, so project templates take precedence

    Returns:
        The complete markdown document.

    Raises:
        TemplateError: If the kind/nature is invalid or templates are missing.
    """
    choice = TemplateChoice(kind=kind, nature=nature)
    template_dir = resolve_template_dir(choice.kind, memory_path)

    today = datetime.now().strftime("%Y-%m-%d")
    tags_str = ", ".join(tags) if tags else ""

    natures = _read_natures(template_dir) if choice.nature else {}
    if choice.nature and choice.nature not in natures:
        raise TemplateError(
            f"Nature '{choice.nature}' is not defined in {template_dir / 'natures.md'}."
        )

    sections: List[str] = []

    for part in ASSEMBLY_ORDER:
        path = template_dir / f"{part}.md"
        if not path.is_file():
            # decisions/dependencies/interface are optional in a custom set.
            if part in ("module", "current"):
                raise TemplateError(f"Required template missing: {path}")
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise TemplateError(f"Could not read {path}: {e}") from e

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


def describe_choices() -> str:
    """Render the available kinds and natures for CLI help."""
    lines = ["Kinds:"]
    for kind in KINDS:
        lines.append(f"  {kind:<16} {KIND_SUMMARY[kind]}")
    lines.append("")
    lines.append(f"Natures ({NATURE_KIND} only):")
    for nature in NATURES:
        lines.append(f"  {nature:<16} {NATURE_SUMMARY[nature]}")
    return "\n".join(lines)
