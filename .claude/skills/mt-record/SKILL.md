---
name: mt-record
description: Records to the memory_tool timeline, searches past work and builds context for an AI session. Use when the user asks "기록해줘", "타임라인에 남겨줘", "record this", "검색해줘", "예전에 어떻게 했었지?", "what did we do about...", "how did we implement X", asks to resume work, or when a project rule says to record or search with m, ms or mcontext.
---

# MT-Record: Timeline, Search and Context

> Capture in the timeline, find it again with search, hand it to the next session with context.

The project's `CLAUDE.md` (or `AGENTS.md`) decides **when** to record and how much. This skill covers **how**. If the project gives no rule, record at natural breakpoints: finish the work, show the result, then ask whether to record it.

## Recording

```bash
m "message"                        # Append to today's timeline
m "Fixed login timeout #bug #auth" # Tags at the end of the message
m "message" --tags bug,auth        # Or as an option
m "message" --date 2026-11-10      # Another day (YYYY-MM-DD)
m "message" --time 14:30           # Set the timestamp (HH:MM)
```

- Record only with `m`. Never create or edit timeline files by hand: `m` keeps the file format and updates the context.
- Write one finding per entry, in a sentence someone can understand later without the conversation.
- Useful prefixes: `Decision: ... because ...`, `Completed: ...`, `Fixed: ...`, `Blocker: ...`, `Starting ...`.
- Small decisions belong in the timeline. A document is only for what someone will look up or need explained later (the `mt-write` skill).
- **Several items at once:** list the entries you would record, ask once, then run one `m` per entry.

## Searching

Search before answering a question about past work. Do not guess from memory.

```bash
ms "query"                     # Timeline and documents of this project
ms "query" --with-kb           # Include the personal knowledge base (other projects)
ms "query" --tag bug           # Filter by tag (repeatable)
ms "query" --date this-week    # today, yesterday, this-week, last-N-days
ms "query" --type timeline     # timeline, modules, decisions, plans
ms "query" --semantic          # Meaning-based search (needs the vector extra)
ms "query" --hybrid            # Keyword and semantic combined
```

1. Search, then show what you found with its date or document path.
2. If nothing turns up locally, try `--with-kb` or a different wording before saying there is nothing.

## Reading the timeline

```bash
mtoday          # Today
mdays 3         # The last three days
mweek           # This week
```

## Context and resuming work

```bash
mcontext                  # Regenerate .claude/memory-context.md
mcontext --days 14        # Cover more recent days
mcontext --with-map       # Also write code-context.md (Python code structure)
mcontext --structure      # Include the module-to-source mapping
```

- `m` updates the context file after each entry, so run `mcontext` when the file is missing or stale.
- **Resuming work:** read the recent timeline (`mweek`) and `git log`. If the project uses Goal Loop, read it as well. There is no status document to maintain.

## Where things are

The knowledge base folder is configurable and is **not always `.memory/`**. Run `mbase show` (or `mbase show --porcelain` for just the name) instead of assuming a path.

## Periodic upkeep

Suggest these when the user asks what to tidy up. Do not run `mreview` on your own: it is a conversation with the user.

```bash
mreview          # Reflect on recent entries and settle what to keep
mcheck           # Verify the paths documents point to
mmodule audit    # Split and merge candidates
```

## Related skills

- Writing or improving a document: `mt-write`
- Publishing a module to the knowledge base: `mt-publish`
- Importing from the knowledge base: `mimport --list`, `mimport <path> --preview`, `mimport <path>`
