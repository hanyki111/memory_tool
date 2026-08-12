import { App, Modal, Notice } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";

export class CreateModuleModal extends Modal {
  private cli: MemoryToolCli;

  constructor(app: App, cli: MemoryToolCli) {
    super(app);
    this.cli = cli;
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

        // Open newly created single-file module in Obsidian
        const modBasename = name.split("/").pop() || name;
        const targetPath = `.memory/modules/${name}/${modBasename}.md`;
        const file = this.app.vault.getAbstractFileByPath(targetPath);

        if (file) {
          // @ts-ignore
          this.app.workspace.getLeaf(false).openFile(file);
        }

        this.close();
      } catch (err: any) {
        new Notice(`Failed to create module: ${err.message}`);
      }
    };

    submitBtn.addEventListener("click", submit);
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
