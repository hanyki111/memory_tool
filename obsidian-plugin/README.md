# Obsidian Memory Tool Integration Plugin

This plugin integrates `memory_tool` with Obsidian, providing fast timeline recording, module management, and AI context building right inside Obsidian.

---

## 🚀 Features

- **⏱️ 0.5s Quick Timeline Record (`Ctrl+Alt+M`)**: Instantly record timeline entries into `.memory/timeline/daily/YYYY-MM/DD.md`.
- **📂 Create Module (`mmodule create`)**: Create single-file markdown modules in `[Folder]/[Folder].md` format and open them immediately.
- **🔍 Quick Module Navigation (`Ctrl+Alt+G`)**: Search active modules and jump to their markdown note.
- **🧠 AI Context Generator (`mcontext`)**: Rebuild `.claude/memory-context.md` from ribbon icon or command.
- **🏥 Path Health Check (`mcheck`)**: Check module health and broken links.

---

## 📅 Obsidian Calendar Integration Setup

To connect Obsidian's **Calendar Plugin** with `memory_tool`'s daily timeline:

1. Open Obsidian **Settings** -> **Daily Notes** (or Periodic Notes).
2. Set **Date Format** to: `YYYY-MM/DD`
3. Set **New file location** to: `.memory/timeline/daily`
4. Now, clicking any date in the Obsidian Calendar will automatically open or create `memory_tool`'s daily timeline file (`.memory/timeline/daily/2026-08/13.md`)!

---

## ⚙️ Installation

1. Open your Obsidian Vault directory.
2. Create directory: `.obsidian/plugins/obsidian-memory-tool/`
3. Copy `manifest.json`, `main.js` (or compiled source), and `styles.css` into `.obsidian/plugins/obsidian-memory-tool/`.
4. Enable **Memory Tool Integration** in Obsidian **Settings** -> **Community plugins**.
