import { App, FuzzySuggestModal, TFile } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";
import { DEFAULT_BASE, moduleCandidatePaths } from "../paths";

export class ModuleSuggestModal extends FuzzySuggestModal<string> {
  private cli: MemoryToolCli;
  private modules: string[] = [];
  private getBaseName: () => string;

  constructor(app: App, cli: MemoryToolCli, getBaseName?: () => string) {
    super(app);
    this.cli = cli;
    this.getBaseName = getBaseName ?? (() => DEFAULT_BASE);
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
    const possiblePaths = moduleCandidatePaths(this.getBaseName(), item);

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
    }
  }
}
