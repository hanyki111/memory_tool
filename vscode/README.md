# Memory Tool Timeline for VS Code

Record to the [memory_tool](https://github.com/hanyki111/memory_tool) timeline, read it back across days, and
search it, without leaving VS Code. The extension works on the knowledge base of the folder open in the window,
found by the same rules as the CLI.

## What it does

- **Record:** type in the box at the top and press Enter. Tags go in the text as `[tag]` at the start or `#tag`
  at the end, as with `m`. Notices such as the review reminder appear as VS Code notifications.
- **Read across days:** the timeline opens on the last seven days, newest first, and within a day too. Scroll to
  the end, or press the button there, for the seven days before, and so on back to the first entries. The screen
  never goes back on its own, so a quiet week shows as a quiet week. Lines written into a timeline file by hand
  are shown in italics under the entry they follow.
- **Choose a period:** under **Period**, pick dates, or use This week, Last week, This month. The screen shows the
  period from its last day and keeps going back as you scroll. **Latest** returns to today.
- **Search:** Enter searches by keyword (about two seconds). **Search by meaning** runs hybrid search, which also
  finds related wording but loads a model on every search (about ten seconds). Timeline hits come first, newest
  first, then documents. A timeline hit opens its week with
  the entry marked; a document hit opens the file at that line. **Back to the timeline** returns to where you
  were.
- **Review:** the **Review** button opens a terminal and runs `mreview`, which covers the entries since the last
  review. To review from another date, open **Period** and use **Review from <date>**. It runs
  `mreview --since <first day on screen>`, from that day until now.
- **Side bar and editor tab:** the Memory Tool icon in the activity bar opens the side bar view; **Open wide** (or
  **Memory Tool: Open Timeline in Editor**) opens the same screen as an editor tab. Both stay in step: an entry
  recorded in one, in a terminal with `m`, or by an agent appears in all of them.

The screen follows VS Code's colours and its display language (Korean or English).

## Requirements

- memory_tool 1.4 or later, for the `--json` output this extension reads.
- A knowledge base in the open folder: run `minit` there first. A folder counts only if its knowledge base holds
  `config.yaml`, which `minit` writes.

Python is looked for in the `memoryTool.python` setting, then the folder's `.venv` (`Scripts/python.exe` or
`bin/python`), then `python` on PATH. It must be able to run `python -m memory_tool`.

With several folders in one window, the first folder is used.

## Not in this version

Editing or deleting entries, recording at another date or time, choosing review items on the screen (the review
runs in the terminal), and Remote SSH, which has not been tried.

## Build

```bash
npm install
npm test            # node --test: the CLI layer (against the real CLI), the state and the screen logic
npm run package     # typecheck, bundle into dist/, and write memory-tool-timeline-<version>.vsix
```

Install the `.vsix` with **Extensions: Install from VSIX...**, or `code --install-extension
memory-tool-timeline-<version>.vsix`.

The tests run `python -m memory_tool` from this checkout on a synthetic knowledge base in a temporary folder. Set
`MEMORY_TOOL_PYTHON` to use another Python.

## How it is built

- `src/cli.ts` runs the CLI with `execFile` and an argument array, never a shell, and reads the one-line JSON
  result. See "JSON Output" in `docs/USER_GUIDE.md` for the format.
- `src/state.ts` and `src/screen.ts` hold what each screen shows and answer its messages. They use no VS Code API,
  so the tests run them with a fake CLI and host.
- `src/extension.ts` registers the views, watches the timeline folder and opens files and terminals.
- `media/timeline.js` draws the screen from what it is sent. Text from the knowledge base is only set with
  `textContent`, and the page's content security policy allows only its own script.
