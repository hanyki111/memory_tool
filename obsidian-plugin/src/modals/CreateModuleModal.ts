import { App, Modal, Notice, TFile } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";
import { DEFAULT_BASE, moduleCandidatePaths } from "../paths";

export class CreateModuleModal extends Modal {
  private cli: MemoryToolCli;
  /** Returns the vault-relative base prefix ("" = the vault root). */
  private getBasePrefix: () => string;

  constructor(app: App, cli: MemoryToolCli, getBasePrefix?: () => string) {
    super(app);
    this.cli = cli;
    this.getBasePrefix = getBasePrefix ?? (() => DEFAULT_BASE);
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("memory-tool-record-modal");

    contentEl.createEl("h3", { text: "📂 Create Module (memory_tool)" });

    // Module Name
    const nameGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    nameGroup.createEl("label", { text: "Module Name or Path (e.g., projects/website or core-system):" });
    const nameInput = nameGroup.createEl("input", {
      type: "text",
      placeholder: "e.g. projects/memory-tool/search-system",
    });
    nameInput.focus();

    // Description
    const descGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    descGroup.createEl("label", { text: "Description (Optional):" });
    const descInput = descGroup.createEl("input", {
      type: "text",
      placeholder: "Short description of this module's purpose",
    });

    // Tags
    const tagsGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    tagsGroup.createEl("label", { text: "Tags (Comma-separated, Optional):" });
    const tagsInput = tagsGroup.createEl("input", {
      type: "text",
      placeholder: "e.g. search, python, cli",
    });

    const buttonsEl = contentEl.createDiv({ cls: "memory-tool-modal-buttons" });
    const cancelBtn = buttonsEl.createEl("button", { text: "Cancel" });
    const submitBtn = buttonsEl.createEl("button", {
      text: "Create Module",
      cls: "mod-cta",
    });

    cancelBtn.addEventListener("click", () => this.close());

    const submit = async () => {
      const name = nameInput.value.trim();
      const desc = descInput.value.trim();
      const tags = tagsInput.value.trim();

      if (!name) {
        new Notice("Module name is required.");
        return;
      }

      try {
        await this.cli.createModule(name, desc, tags);
        new Notice(`Module created: ${name}`);

        // Open the new single-file module, under the configured base folder.
        // memory_tool wrote it outside Obsidian, so the vault cache may not have
        // picked it up yet -- retry briefly before giving up.
        const candidates = moduleCandidatePaths(this.getBasePrefix(), name);
        const opened = await this.openWhenAvailable(candidates);

        if (!opened) {
          new Notice(
            `Module created, but could not open it in this vault. Looked in: ` +
              `${candidates.join(", ")}. Check the Knowledge Base Folder setting.`,
            8000
          );
        }

        this.close();
      } catch (err: any) {
        new Notice(`Failed to create module: ${err.message}`);
      }
    };

    submitBtn.addEventListener("click", submit);
  }

  /**
   * Open the first candidate path that appears in the vault.
   *
   * Files created by memory_tool arrive from outside Obsidian, so the vault
   * index can lag by a moment. Polls briefly rather than failing immediately.
   */
  private async openWhenAvailable(candidates: string[]): Promise<boolean> {
    const attempts = 10;
    const delayMs = 100;

    for (let i = 0; i < attempts; i++) {
      for (const path of candidates) {
        const file = this.app.vault.getAbstractFileByPath(path);
        if (file instanceof TFile) {
          await this.app.workspace.getLeaf(false).openFile(file);
          return true;
        }
      }
      await new Promise((resolve) => window.setTimeout(resolve, delayMs));
    }
    return false;
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
