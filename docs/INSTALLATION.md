# Installation Guide

> Complete installation instructions for memory_tool

---

## System Requirements

### Minimum Requirements

- **Python:** 3.10 or higher
- **OS:** Windows, macOS, or Linux
- **Git:** Required for GitHub installation
- **Disk Space:** ~100MB (base) + additional for optional features

### Recommended

- **Python:** 3.11 or 3.12 (better performance)
- **Terminal:** PowerShell 7+ (Windows) or modern shell (Unix)
- **Editor:** Claude Code, VS Code, or any editor with terminal

---

## Installation Methods

### Method 1: GitHub Installation (Recommended) ⭐

This is the simplest and recommended method for most users.

#### Basic Installation

```bash
pip install git+https://github.com/hanyki111/memory_tool.git
```

#### Specific Version

```bash
# Install a specific release
pip install git+https://github.com/hanyki111/memory_tool.git@v1.0.0-alpha

# Install from a specific branch
pip install git+https://github.com/hanyki111/memory_tool.git@feature-branch
```

#### Verification

```bash
# Check installation
python -m memory_tool --version

# Test basic command
m "Installation test"
```

---

### Method 2: Development Installation

For contributors or users who want to modify the source code.

#### Clone and Install

```bash
# Clone the repository
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool

# Install in editable mode
pip install -e .
```

#### With Development Dependencies

```bash
# Install with dev tools (pytest, black, ruff)
pip install -e .[dev]
```

#### Verification

```bash
# Run from source
python -m memory_tool --version

# Your changes will be immediately reflected
```

---

## Optional Features

memory_tool supports optional features that can be installed separately.

### Vector Search (Semantic Search)

Enable semantic/vector search capabilities using sentence-transformers.

```bash
# Install vector search support
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[vector]
```

**Requirements:**
- ~500MB additional disk space
- 2GB+ RAM recommended
- GPU optional (CPU works but slower)

**What you get:**
- `ms --semantic "query"` - Semantic search
- `ms --hybrid "query"` - Combined text + semantic search
- Better search for conceptual queries

### LLM Features

Enable AI-powered features like summarization and suggestions.

```bash
# Install LLM support
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[llm]
```

**Requirements:**
- Anthropic API key (for Claude) OR
- Ollama installed locally (free, offline)

**What you get:**
- `msummary` - Summarize timeline or modules
- `module suggest-ai` - AI-based connection suggestions
- `module auto-tag` - Automatic tagging

**Configuration:**
```yaml
# .memory/config.yaml
llm:
  provider: ollama  # or 'anthropic'
  model: llama2     # or 'claude-3-haiku-20240307'
  # For Anthropic:
  # api_key: sk-...  # or set ANTHROPIC_API_KEY env var
```

### TUI Browser

Enable the interactive Terminal UI browser.

```bash
# Install TUI support
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[tui]
```

**What you get:**
- `mbrowse` - Interactive TUI browser
- Multi-mode interface (Search/Timeline/Modules/Graph)
- Vim-style navigation
- Rich visual display

### Shell Completion

Enable shell auto-completion for commands.

```bash
# Install completion support
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[completion]
```

**What you get:**
- `mcompletion install bash` - Bash completion
- `mcompletion install zsh` - Zsh completion
- `mcompletion install fish` - Fish completion

### Install Everything

```bash
# Install all optional features
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[vector,llm,tui,completion]
```

---

## Initial Setup

After installation, initialize your first project.

### 1. Navigate to Your Project

```bash
cd /path/to/your/project
```

### 2. Initialize .memory/

```bash
minit
```

This creates:
```
.memory/
├── timeline/          # Time-based entries
├── modules/           # Space-based organization
├── concepts/          # Conceptual knowledge
├── config.yaml        # Configuration
└── .connections.db    # Graph database
```

### 3. First Record

```bash
m "프로젝트 시작! memory_tool 설치 완료"
```

### 4. Verify

```bash
# View today's timeline
mtoday

# Search
ms "프로젝트"

# Check status
mstatus
```

---

## Optional: Install Aliases

Aliases make commands shorter and more convenient.

### Windows Batch Files

```bash
# Install all aliases
malias install

# Install specific aliases
malias install m ms mtoday
```

**Result:** Creates `.bat` files in `%USERPROFILE%\.memory\bin\`

**Manual PATH addition (if needed):**
```powershell
# Add to PATH (PowerShell as Admin)
$path = [Environment]::GetEnvironmentVariable("Path", "User")
$newPath = "$env:USERPROFILE\.memory\bin"
[Environment]::SetEnvironmentVariable("Path", "$path;$newPath", "User")
```

### PowerShell Profile (Recommended)

```bash
# Install to PowerShell profile
malias install --powershell
```

**Result:** Works in all terminals (PowerShell, VS Code, Windows Terminal)

**Verification:**
```powershell
# Restart terminal, then:
m "테스트"
```

### Unix (Bash/Zsh)

```bash
# Install shell functions
malias install --shell bash  # or zsh

# Add to your profile
echo 'source ~/.memory/aliases.sh' >> ~/.bashrc  # or ~/.zshrc

# Reload
source ~/.bashrc
```

---

## Configuration

### Create config.yaml

The first time you run `minit`, a default config is created at `.memory/config.yaml`.

### Basic Configuration

```yaml
# .memory/config.yaml
timeline:
  auto_sort: true         # Auto-sort entries by time
  default_format: "HH:MM" # Time format

modules:
  auto_discover: true     # Auto-discover hierarchical modules
  default_template: standard

search:
  default_mode: text      # text | semantic | hybrid
  cache_results: true
  cache_ttl: 3600        # 1 hour

context:
  auto_update: true       # Auto-update after record
  max_timeline_entries: 10
  max_modules: 5

llm:
  provider: ollama        # anthropic | ollama
  model: llama2          # Model name
  # api_key: sk-...      # For Anthropic (or use env var)
```

### Environment Variables

```bash
# Anthropic API (for LLM features)
export ANTHROPIC_API_KEY=sk-ant-...

# Ollama host (if not default)
export OLLAMA_HOST=http://localhost:11434
```

---

## Troubleshooting

### Installation Issues

#### "Command not found: pip"

**Solution:**
```bash
# Ensure Python is installed
python --version

# Use python -m pip instead
python -m pip install git+https://github.com/hanyki111/memory_tool.git
```

#### "Permission denied"

**Solution:**
```bash
# Install for user only (no sudo)
pip install --user git+https://github.com/hanyki111/memory_tool.git
```

#### "Git not found"

**Solution:**
- Install Git: https://git-scm.com/downloads
- Or use development installation (clone manually)

### Version Conflicts

#### "Dependency conflict"

**Solution:**
```bash
# Use virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# Install in clean environment
pip install git+https://github.com/hanyki111/memory_tool.git
```

### Runtime Issues

#### "Command not found: m"

**Cause:** Aliases not installed or PATH not set

**Solution:**
```bash
# Use full command
python -m memory_tool record "message"

# Or reinstall aliases
malias install --powershell  # Windows
```

#### "Encoding error" (Windows)

**Cause:** Windows console encoding

**Solution:**
```powershell
# Set UTF-8 encoding
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# Or use modern terminal (Windows Terminal)
```

#### "Vector search slow"

**Cause:** CPU-only processing

**Solution:**
```bash
# Check if GPU available
python -c "import torch; print(torch.cuda.is_available())"

# If True, install with GPU support
pip uninstall sentence-transformers
pip install sentence-transformers[gpu]
```

---

## Verification Checklist

After installation, verify everything works:

- [ ] `python -m memory_tool --version` shows version
- [ ] `minit` creates `.memory/` directory
- [ ] `m "test"` records to timeline
- [ ] `ms "test"` finds the entry
- [ ] `mtoday` shows today's timeline
- [ ] `mstatus` shows statistics
- [ ] Aliases work (if installed)

**Optional features:**
- [ ] `ms --semantic "test"` works (if vector installed)
- [ ] `msummary` works (if llm installed)
- [ ] `mbrowse` launches (if tui installed)

---

## Next Steps

✅ **Installation complete!**

Continue to:
- 📚 [QUICKSTART.md](QUICKSTART.md) - 5-minute start guide
- 📖 [USER_GUIDE.md](USER_GUIDE.md) - Complete user guide
- ❓ [FAQ.md](FAQ.md) - Frequently asked questions

---

## Uninstallation

If you need to remove memory_tool:

```bash
# Uninstall package
pip uninstall memory-tool

# Remove aliases (optional)
malias uninstall

# Remove data (optional - this deletes all your data!)
# rm -rf .memory/  # Unix
# rmdir /s .memory  # Windows
```

**Note:** Uninstalling the package does NOT delete your `.memory/` data. Your data remains safe unless you explicitly delete it.

---

**Need help?** Open an issue: https://github.com/hanyki111/memory_tool/issues
