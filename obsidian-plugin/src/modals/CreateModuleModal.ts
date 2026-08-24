import { App, Modal, Notice, TFile } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";
import { DEFAULT_BASE, moduleCandidatePaths } from "../paths";
import {
  KINDS,
  ModuleKind,
  ModuleNature,
  NATURES_BY_KIND,
} from "../moduleKinds";

/**
 * Create a module, asking the two MOP decision questions first.
 *
 * The answers are passed to `mmodule create --kind --nature`; memory_tool owns
 * template resolution and assembly, including the project-over-bundled override
 * and the Nature outline splice. The modal's job is only to make the two
 * questions unavoidable at the moment the module is created, which is the point
 * at which they are cheap to answer and easy to skip.
 */
export class CreateModuleModal extends Modal {
  private cli: MemoryToolCli;
  private getBasePrefix: () => string;

  private kind: ModuleKind = "knowledge";
  private nature: ModuleNature | undefined = "concept";
  private draft = false;

  constructor(app: App, cli: MemoryToolCli, getBasePrefix?: () => string) {
    super(app);
    this.cli = cli;
    this.getBasePrefix = getBasePrefix ?? (() => DEFAULT_BASE);
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
    nameInput.focus();

    const descGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    descGroup.createEl("label", { text: "목적 (한 문장)" });
    const descInput = descGroup.createEl("input", {
      type: "text",
      placeholder: "두 문장이 넘어가면 모듈을 분리하라는 신호입니다",
    });

    const tagsGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    tagsGroup.createEl("label", { text: "태그 (쉼표 구분, 선택)" });
    const tagsInput = tagsGroup.createEl("input", {
      type: "text",
      placeholder: "예: search, python, cli",
    });

    // --- Kind: the one question that decides the template ---
    const kindGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    kindGroup.createEl("label", {
      text: "Kind — 이 문서가 서술하는 대상이 이미 존재하는가?",
    });
    const kindSelect = kindGroup.createEl("select");
    for (const k of KINDS) {
      kindSelect.createEl("option", { value: k.id, text: `${k.answer} → ${k.id}` });
    }
    kindSelect.value = this.kind;

    // --- Nature: knowledge and intent, each with its own set ---
    const natureGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    natureGroup.createEl("label", { text: "Nature — 무엇이 이 모듈을 갱신시키는가?" });
    const natureSelect = natureGroup.createEl("select");
    const natureHint = natureGroup.createDiv({ cls: "memory-tool-hint" });

    const syncNatureHint = () => {
      const chosen = NATURES_BY_KIND[this.kind].find(
        (n) => n.id === natureSelect.value
      );
      natureHint.setText(chosen ? `답하는 질문: ${chosen.answers}` : "");
    };

    // The two sets share no names, so the options are rebuilt on every Kind
    // change rather than filtered -- a leftover selection from the other set
    // would be rejected by `mmodule create`.
    const syncNatureOptions = () => {
      const options = NATURES_BY_KIND[this.kind];
      natureSelect.empty();
      natureGroup.toggleClass("memory-tool-hidden", options.length === 0);

      for (const n of options) {
        natureSelect.createEl("option", {
          value: n.id,
          text: `${n.trigger} → ${n.label} · ${n.lifetime}`,
        });
      }

      this.nature = options.length ? options[0].id : undefined;
      if (options.length) {
        natureSelect.value = options[0].id;
      }
      syncNatureHint();
    };
    syncNatureOptions();

    natureSelect.addEventListener("change", () => {
      this.nature = natureSelect.value as ModuleNature;
      syncNatureHint();
    });

    kindSelect.addEventListener("change", () => {
      this.kind = kindSelect.value as ModuleKind;
      syncNatureOptions();
    });

    // --- Draft: the seed document, for a module being started from nothing ---
    const draftGroup = contentEl.createDiv({ cls: "memory-tool-form-group" });
    const draftLabel = draftGroup.createEl("label");
    const draftToggle = draftLabel.createEl("input", { type: "checkbox" });
    draftLabel.appendText(" 초안으로 시작 (--draft)");
    draftGroup.createDiv({
      cls: "memory-tool-hint",
      text:
        "전체 골격 대신 40줄짜리 씨앗 문서를 만듭니다. " +
        "필요해지면 'mmodule grow' 로 나머지 절을 붙입니다.",
    });

    draftToggle.addEventListener("change", () => {
      this.draft = draftToggle.checked;
    });

    // --- Buttons ---
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
    await this.cli.createModule(
      name,
      description,
      tags,
      this.kind,
      this.nature,
      this.draft
    );

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

    const base = this.nature ? `${this.kind} / ${this.nature}` : this.kind;
    const label = this.draft ? `${base} (draft)` : base;
    new Notice(`모듈 생성: ${name} (${label})`);
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
