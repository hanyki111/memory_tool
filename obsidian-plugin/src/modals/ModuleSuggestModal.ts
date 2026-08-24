import { App, FuzzySuggestModal, Notice, TFile } from "obsidian";
import { DEFAULT_BASE, moduleCandidatePaths } from "../paths";

export class ModuleSuggestModal extends FuzzySuggestModal<string> {
  /**
   * Supplies the module list.
   *
   * Injected rather than calling the CLI directly so the same modal works on
   * mobile, where the list comes from a vault scan instead of `mmodule list`.
   */
  private lister: () => Promise<string[]>;
  private modules: string[] = [];
  /** Returns the vault-relative base prefix ("" = the vault root). */
  private getBasePrefix: () => string;
  /**
   * What to do with the chosen module. Defaults to opening it, which is what
   * "모듈로 이동" wants; other callers act on the name instead.
   */
  private onChoose: ((name: string) => void) | null;

  constructor(
    app: App,
    lister: () => Promise<string[]>,
    getBasePrefix?: () => string,
    onChoose?: (name: string) => void
  ) {
    super(app);
    this.lister = lister;
    this.getBasePrefix = getBasePrefix ?? (() => DEFAULT_BASE);
    this.onChoose = onChoose ?? null;
    this.setPlaceholder("Type to search active memory_tool modules...");
  }

  async onOpen() {
    super.onOpen();
    this.modules = await this.lister();
  }

  getItems(): string[] {
    return this.modules;
  }

  getItemText(item: string): string {
    return item;
  }

  onChooseItem(item: string, evt: MouseEvent | KeyboardEvent): void {
    if (this.onChoose) {
      this.onChoose(item);
      return;
    }

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
