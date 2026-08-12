import { App, FuzzySuggestModal, TFile } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";

export class ModuleSuggestModal extends FuzzySuggestModal<string> {
  private cli: MemoryToolCli;
  private modules: string[] = [];

  constructor(app: App, cli: MemoryToolCli) {
    super(app);
    this.cli = cli;
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
    const modBasename = item.split("/").pop() || item;
    // Follows [Folder]/[Folder].md convention
    const possiblePaths = [
      `.memory/modules/${item}/${modBasename}.md`,
      `.memory/modules/${item}.md`,
    ];

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
