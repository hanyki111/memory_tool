import { App, Modal, Notice, TFile } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";
import { DEFAULT_BASE, moduleCandidatePaths } from "../paths";
import { DOCUMENT_TYPES } from "../documentTypes";

/**
 * Create a document: a path, and optionally a type and one sentence.
 *
 * memory_tool writes the file, which holds frontmatter and a title. The body is
 * the writer's, so nothing here adds sections or asks about structure.
 */
export class CreateModuleModal extends Modal {
  private cli: MemoryToolCli;
  private getBasePrefix: () => string;

  /** Pre-filled module path, from a right-clicked folder. */
  private initialPath: string;

  private docType = "";

  constructor(
    app: App,
    cli: MemoryToolCli,
    getBasePrefix?: () => string,
    initialPath = ""
  ) {
    super(app);
    this.cli = cli;
    this.getBasePrefix = getBasePrefix ?? (() => DEFAULT_BASE);
    this.initialPath = initialPath;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("memory-tool-record-modal");

    contentEl.createEl("h3", { text: "모듈 생성" });

    // --- Name / description / tags ---
    const nameGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    nameGroup.createEl("label", { text: "모듈 경로" });
    const nameInput = nameGroup.createEl("input", {
      type: "text",
      placeholder: "예: 게임 분석/니케/전투 공식",
    });

    // Opened from a folder: the parent path is already known, so only the leaf
    // name is left to type and the caret starts after the trailing slash.
    if (this.initialPath) {
      nameInput.value = `${this.initialPath}/`;
      nameGroup.createDiv({
        cls: "memory-tool-hint",
        text: `${this.initialPath}/ 아래에 만듭니다.`,
      });
    }
    nameInput.focus();
    nameInput.setSelectionRange(nameInput.value.length, nameInput.value.length);

    const descGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    descGroup.createEl("label", { text: "설명 (한 문장, 선택)" });
    const descInput = descGroup.createEl("input", {
      type: "text",
      placeholder: "한 문장으로 쓰기 어려우면 문서를 나눌 신호입니다",
    });

    const tagsGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    tagsGroup.createEl("label", { text: "태그 (쉼표 구분, 선택)" });
    const tagsInput = tagsGroup.createEl("input", {
      type: "text",
      placeholder: "예: search, python, cli",
    });

    // --- Type: optional, and free to stay empty ---
    const typeGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    typeGroup.createEl("label", { text: "종류 (선택)" });
    const typeSelect = typeGroup.createEl("select");
    typeSelect.createEl("option", { value: "", text: "정하지 않음" });
    for (const option of DOCUMENT_TYPES) {
      typeSelect.createEl("option", {
        value: option.id,
        text: `${option.id}: ${option.answers}`,
      });
    }
    const typeHint = typeGroup.createDiv({ cls: "memory-tool-hint" });

    typeSelect.addEventListener("change", () => {
      this.docType = typeSelect.value;
      const chosen = DOCUMENT_TYPES.find((option) => option.id === this.docType);
      typeHint.setText(chosen ? `갱신 계기: ${chosen.updatedWhen}` : "");
    });

    const buttonsEl = contentEl.createDiv({ cls: "memory-tool-modal-buttons" });
    const cancelBtn = buttonsEl.createEl("button", { text: "취소" });
    const submitBtn = buttonsEl.createEl("button", { text: "생성", cls: "mod-cta" });

    cancelBtn.addEventListener("click", () => this.close());

    submitBtn.addEventListener("click", async () => {
      const name = nameInput.value.trim();
      if (!name) {
        new Notice("모듈 경로를 입력하세요.");
        return;
      }

      submitBtn.setAttr("disabled", "true");
      try {
        await this.create(name, descInput.value.trim(), tagsInput.value.trim());
        this.close();
      } catch (err: any) {
        new Notice(`모듈 생성 실패: ${err.message}`);
        submitBtn.removeAttribute("disabled");
      }
    });
  }

  private async create(name: string, description: string, tags: string): Promise<void> {
    await this.cli.createModule(name, description, tags, this.docType);

    const basePrefix = this.getBasePrefix();
    const candidates = moduleCandidatePaths(basePrefix, name);
    const path = await this.waitForFile(candidates);

    if (!path) {
      new Notice(
        `모듈은 생성됐지만 vault에서 열지 못했습니다. 확인한 경로: ${candidates.join(", ")}`,
        8000
      );
      return;
    }

    await this.openPath(path);

    new Notice(this.docType ? `모듈 생성: ${name} (${this.docType})` : `모듈 생성: ${name}`);
  }

  /**
   * Wait for the file memory_tool just wrote to become visible.
   *
   * It is created outside Obsidian, so both the adapter and the file index can
   * lag by a moment; polling briefly beats failing on the first miss.
   */
  private async waitForFile(candidates: string[]): Promise<string | null> {
    for (let i = 0; i < 15; i++) {
      for (const path of candidates) {
        if (await this.app.vault.adapter.exists(path)) return path;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 100));
    }
    return null;
  }

  private async openPath(path: string): Promise<void> {
    const file = this.app.vault.getAbstractFileByPath(path);
    if (file instanceof TFile) {
      await this.app.workspace.getLeaf(false).openFile(file);
    }
  }

  onClose() {
    this.contentEl.empty();
  }
}
