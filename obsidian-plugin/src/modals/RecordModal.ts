import { App, Modal, Notice } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";

export class RecordModal extends Modal {
  private cli: MemoryToolCli;

  constructor(app: App, cli: MemoryToolCli) {
    super(app);
    this.cli = cli;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("memory-tool-record-modal");

    contentEl.createEl("h3", { text: "⏱️ Quick Timeline Record (memory_tool)" });

    const textArea = contentEl.createEl("textarea", {
      cls: "memory-tool-input-textarea",
      placeholder: "Write what you are doing or thinking... (Ctrl+Enter or Enter to submit)",
    });

    textArea.focus();

    const buttonsEl = contentEl.createDiv({ cls: "memory-tool-modal-buttons" });
    const cancelBtn = buttonsEl.createEl("button", { text: "Cancel" });
    const submitBtn = buttonsEl.createEl("button", {
      text: "Record (0.5s)",
      cls: "mod-cta",
    });

    cancelBtn.addEventListener("click", () => this.close());

    const submit = async () => {
      const text = textArea.value.trim();
      if (!text) {
        new Notice("Please enter a timeline message.");
        return;
      }

      try {
        await this.cli.recordTimeline(text);
        new Notice(`Recorded to timeline: "${text}"`);
        this.close();
      } catch (err: any) {
        new Notice(`Failed to record timeline: ${err.message}`);
      }
    };

    submitBtn.addEventListener("click", submit);

    textArea.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
        e.preventDefault();
        submit();
      }
    });
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
