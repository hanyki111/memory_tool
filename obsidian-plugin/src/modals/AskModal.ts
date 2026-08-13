import {
  App,
  Component,
  MarkdownRenderer,
  Modal,
  Notice,
  Setting,
  TFile,
} from "obsidian";
import { AskResult, MemoryToolCli } from "../cli/memoryToolCli";
import { underBase } from "../paths";

/**
 * Ask a natural-language question about the knowledge base (mask).
 *
 * The answer comes from an LLM, so it can take tens of seconds. The modal stays
 * open and shows progress rather than blocking on a Notice, and the answer is
 * rendered as Markdown so lists, code and links look right. The question box
 * stays available so follow-up questions do not require reopening the modal.
 */
export class AskModal extends Modal {
  private cli: MemoryToolCli;
  private getBasePrefix: () => string;

  private inputEl!: HTMLTextAreaElement;
  private statusEl!: HTMLElement;
  private answerEl!: HTMLElement;
  private submitBtn!: HTMLButtonElement;
  private insertBtn!: HTMLButtonElement;

  private running = false;
  private lastResult: AskResult | null = null;

  /**
   * Owns the lifecycle of rendered Markdown. MarkdownRenderer attaches child
   * components (embeds, code blocks) that must be unloaded with the modal;
   * Modal is not itself a Component, so it cannot serve as that owner.
   */
  private renderHost = new Component();

  /** Keyword RAG instead of the tool-using agent: faster, less thorough. */
  private simpleMode = false;

  constructor(app: App, cli: MemoryToolCli, getBasePrefix?: () => string) {
    super(app);
    this.cli = cli;
    this.getBasePrefix = getBasePrefix ?? (() => "");
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("memory-tool-ask-modal");

    this.renderHost.load();

    contentEl.createEl("h3", { text: "🤔 Ask Your Memory (mask)" });

    this.inputEl = contentEl.createEl("textarea", {
      cls: "memory-tool-input-textarea",
      placeholder:
        "Ask about your knowledge base... e.g. 어제 무슨 작업을 했나요? (Ctrl+Enter to ask)",
    });
    this.inputEl.focus();

    new Setting(contentEl)
      .setName("Fast mode")
      .setDesc(
        "Keyword search instead of the tool-using agent. Quicker, but it cannot " +
          "follow up on what it finds."
      )
      .addToggle((toggle) =>
        toggle.setValue(this.simpleMode).onChange((value) => {
          this.simpleMode = value;
        })
      );

    const buttonsEl = contentEl.createDiv({ cls: "memory-tool-modal-buttons" });

    const closeBtn = buttonsEl.createEl("button", { text: "Close" });
    closeBtn.addEventListener("click", () => this.close());

    this.insertBtn = buttonsEl.createEl("button", { text: "Insert into note" });
    this.insertBtn.disabled = true;
    this.insertBtn.addEventListener("click", () => this.insertIntoNote());

    this.submitBtn = buttonsEl.createEl("button", {
      text: "Ask",
      cls: "mod-cta",
    });
    this.submitBtn.addEventListener("click", () => this.run());

    this.statusEl = contentEl.createDiv({ cls: "memory-tool-ask-status" });
    this.answerEl = contentEl.createDiv({ cls: "memory-tool-ask-answer" });

    this.inputEl.addEventListener("keydown", (e: KeyboardEvent) => {
      // Plain Enter inserts a newline here: questions are often multi-line,
      // unlike the one-line timeline entries in RecordModal.
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        this.run();
      }
    });
  }

  private async run(): Promise<void> {
    if (this.running) return;

    const question = this.inputEl.value.trim();
    if (!question) {
      new Notice("Please enter a question.");
      return;
    }

    this.running = true;
    this.submitBtn.disabled = true;
    this.submitBtn.setText("Thinking...");
    this.insertBtn.disabled = true;
    this.answerEl.empty();

    const started = Date.now();
    this.statusEl.setText("Searching memory and asking the model...");

    // A visible elapsed counter: an LLM round trip can run for a minute and
    // silence is indistinguishable from a hang.
    const ticker = window.setInterval(() => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      this.statusEl.setText(`Searching memory and asking the model... ${seconds}s`);
    }, 1000);

    try {
      const result = await this.cli.ask(question, { simple: this.simpleMode });
      this.lastResult = result;
      await this.renderAnswer(result, Date.now() - started);
      this.insertBtn.disabled = false;
    } catch (err: any) {
      this.lastResult = null;
      this.statusEl.setText("");
      this.answerEl.empty();
      this.answerEl.createEl("p", {
        text: `Failed to answer: ${err.message}`,
        cls: "memory-tool-ask-error",
      });
    } finally {
      window.clearInterval(ticker);
      this.running = false;
      this.submitBtn.disabled = false;
      this.submitBtn.setText("Ask");
    }
  }

  private async renderAnswer(result: AskResult, elapsedMs: number): Promise<void> {
    const seconds = (elapsedMs / 1000).toFixed(1);
    const modeLabel = result.mode === "simple" ? "fast" : "agent";
    this.statusEl.setText(`${result.provider} · ${modeLabel} · ${seconds}s`);

    this.answerEl.empty();

    // Render as Markdown so lists, tables and code blocks display properly.
    await MarkdownRenderer.render(
      this.app,
      result.answer || "_(empty answer)_",
      this.answerEl,
      "",
      this.renderHost
    );

    if (result.tools.length) {
      this.answerEl.createEl("p", {
        text: `Tools used: ${result.tools.join(", ")}`,
        cls: "memory-tool-ask-meta",
      });
    }

    if (result.sources.length) {
      const details = this.answerEl.createEl("details", {
        cls: "memory-tool-ask-sources",
      });
      details.createEl("summary", { text: `Sources (${result.sources.length})` });
      const list = details.createEl("ul");

      for (const source of result.sources) {
        const item = list.createEl("li");
        const vaultPath = this.toVaultPath(source);
        const file = vaultPath
          ? this.app.vault.getAbstractFileByPath(vaultPath)
          : null;

        if (file instanceof TFile) {
          const link = item.createEl("a", { text: vaultPath!, href: "#" });
          link.addEventListener("click", (e) => {
            e.preventDefault();
            this.app.workspace.getLeaf(false).openFile(file);
            this.close();
          });
        } else {
          // Outside the vault, or not indexed yet -- show it as plain text
          // rather than a link that would do nothing.
          item.setText(source);
        }
      }
    }
  }

  /**
   * Convert a memory_tool source path into a vault-relative path.
   *
   * memory_tool reports paths relative to the *project root* (for example
   * ".memory/timeline/..."), while the vault root may be the base folder
   * itself. Re-anchoring through the base prefix keeps links working in both
   * layouts.
   */
  private toVaultPath(source: string): string | null {
    const normalized = source.replace(/\\/g, "/").replace(/^\.\//, "");
    if (!normalized) return null;

    const prefix = this.getBasePrefix();

    // Already vault-relative (the prefix is how the vault sees the base).
    if (this.app.vault.getAbstractFileByPath(normalized)) return normalized;

    // Reported relative to the project root: strip the base folder segment and
    // re-apply the vault-relative prefix.
    const segments = normalized.split("/");
    if (segments.length > 1) {
      const withoutBase = segments.slice(1).join("/");
      const candidate = underBase(prefix, withoutBase);
      if (this.app.vault.getAbstractFileByPath(candidate)) return candidate;
    }

    return null;
  }

  /** Append the question and answer to the active note. */
  private async insertIntoNote(): Promise<void> {
    if (!this.lastResult) return;

    const file = this.app.workspace.getActiveFile();
    if (!file) {
      new Notice("Open a note first, then insert the answer.");
      return;
    }

    const { question, answer, provider, mode } = this.lastResult;
    const block =
      `\n> [!question] ${question}\n` +
      `> _memory_tool · ${provider} · ${mode}_\n\n` +
      `${answer}\n`;

    try {
      await this.app.vault.append(file, block);
      new Notice(`Answer appended to ${file.basename}`);
    } catch (err: any) {
      new Notice(`Could not insert the answer: ${err.message}`);
    }
  }

  onClose() {
    this.renderHost.unload();
    const { contentEl } = this;
    contentEl.empty();
  }
}
