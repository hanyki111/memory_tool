import { App, FuzzySuggestModal, Notice, TFile } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";
import { DEFAULT_BASE, moduleCandidatePaths } from "../paths";

export class ModuleSuggestModal extends FuzzySuggestModal<string> {
  private cli: MemoryToolCli;
  private modules: string[] = [];
  /** Returns the vault-relative base prefix ("" = the vault root). */
  private getBasePrefix: () => string;

  constructor(app: App, cli: MemoryToolCli, getBasePrefix?: () => string) {
    super(app);
    this.cli = cli;
    this.getBasePrefix = getBasePrefix ?? (() => DEFAULT_BASE);
    this.setPlaceholder("Type to search active memory_tool modules...");
  }

  async onOpen() {
    super.onOpen();
    this.modules = await this.cli.listModules();
  }

  getItems(): string[] {
    return this.modules;
  }

  getItemText(item: string): string {
    return item;
  }

  onChooseItem(item: string, evt: MouseEvent | KeyboardEvent): void {
    // Follows [Folder]/[Folder].md convention, under the configured base folder
    const possiblePaths = moduleCandidatePaths(this.getBasePrefix(), item);

    let foundFile: TFile | null = null;

    for (const p of possiblePaths) {
      const abstractFile = this.app.vault.getAbstractFileByPath(p);
      if (abstractFile instanceof TFile) {
        foundFile = abstractFile;
        break;
      }
    }

    if (foundFile) {
      this.app.workspace.getLeaf(false).openFile(foundFile);
      return;
    }

    // Say why nothing opened -- a wrong base folder used to fail silently here.
    new Notice(
      `Could not find '${item}' in this vault. Looked in: ` +
        `${possiblePaths.join(", ")}. Check the Knowledge Base Folder setting.`,
      8000
    );
  }
}
