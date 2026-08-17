/**
 * The memory_tool side panel.
 *
 * One view with stacked, collapsible sections rather than several views: the
 * whole point is seeing capture, today's entries and module navigation at the
 * same time, and separate views would each claim their own tab and defeat that.
 *
 * The capture box being permanently on screen is what makes the panel worth
 * having. A modal -- however fast -- costs a deliberate "open the thing" step
 * before any typing happens, and that step is the actual friction in a 0.5s
 * capture promise.
 */

import { ItemView, Notice, TFile, WorkspaceLeaf, setIcon } from "obsidian";
import { MemoryToolCli } from "../cli/memoryToolCli";
import { candidatePaths } from "../timeline/format";
import { moduleCandidatePaths, describePrefix } from "../paths";

export const MEMORY_PANEL_VIEW = "memory-tool-panel";

/** What the panel needs from the plugin, kept narrow to avoid a cyclic import. */
export interface PanelHost {
  cli: MemoryToolCli;
  basePrefix: string;
  /** Record an entry through whichever path is configured. */
  recordEntry(message: string): Promise<{ path: string; entry: string }>;
  /** Modules, from the CLI when available and a vault scan otherwise. */
  listModules(): Promise<string[]>;
  /** False on mobile, where there is no Python to run. */
  cliAvailable(): boolean;
  /** Number of entries written directly and not yet in the search index. */
  pendingIndexCount(): number;
  /** Reconcile the search index with directly-written entries. */
  syncIndex(): Promise<void>;
}

export class MemoryPanelView extends ItemView {
  private host: PanelHost;

  private captureInput!: HTMLTextAreaElement;
  private todayList!: HTMLElement;
  private moduleList!: HTMLElement;
  private moduleFilter!: HTMLInputElement;
  private statusEl!: HTMLElement;

  private modules: string[] = [];

  constructor(leaf: WorkspaceLeaf, host: PanelHost) {
    super(leaf);
    this.host = host;
  }

  getViewType(): string {
    return MEMORY_PANEL_VIEW;
  }

  getDisplayText(): string {
    return "Memory Tool";
  }

  getIcon(): string {
    return "clock";
  }

  async onOpen(): Promise<void> {
    const root = this.contentEl;
    root.empty();
    root.addClass("memory-tool-panel");

    this.buildCapture(root);
    this.buildToday(root);
    this.buildModules(root);
    this.buildActions(root);

    await this.refreshToday();
    void this.refreshModules();
  }

  async onClose(): Promise<void> {
    this.contentEl.empty();
  }

  /** Focus the capture box; used by the "capture" command. */
  focusCapture(): void {
    this.captureInput?.focus();
  }

  // --- Capture -------------------------------------------------------------

  private buildCapture(root: HTMLElement): void {
    const section = root.createDiv({ cls: "memory-tool-capture" });

    this.captureInput = section.createEl("textarea", {
      cls: "memory-tool-capture-input",
      attr: {
        rows: "2",
        placeholder: "지금 무엇을 하고 있나요?  Enter로 기록, Shift+Enter 줄바꿈",
      },
    });

    this.statusEl = section.createDiv({ cls: "memory-tool-capture-status" });

    this.captureInput.addEventListener("keydown", (e: KeyboardEvent) => {
      // isComposing is essential, not defensive: with a Korean IME the Enter that
      // commits a composition fires keydown too, so without this guard the entry
      // is submitted mid-syllable and the last character is lost.
      if (e.isComposing || e.keyCode === 229) return;

      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void this.submitCapture();
      }
    });
  }

  private async submitCapture(): Promise<void> {
    const text = this.captureInput.value.trim();
    if (!text) return;

    // Clear immediately so the next thought can be typed while this one lands.
    this.captureInput.value = "";

    try {
      const result = await this.host.recordEntry(text);
      this.setStatus(`기록됨 · ${result.entry.slice(0, 60)}`, false);
      await this.refreshToday();
    } catch (err: any) {
      // Put the text back rather than losing it to a failed write.
      this.captureInput.value = text;
      this.setStatus(`기록 실패: ${err.message}`, true);
    }
  }

  private setStatus(text: string, isError: boolean): void {
    this.statusEl.setText(text);
    this.statusEl.toggleClass("memory-tool-status-error", isError);
  }

  // --- Today ---------------------------------------------------------------

  private buildToday(root: HTMLElement): void {
    const details = root.createEl("details", { cls: "memory-tool-section" });
    details.setAttr("open", "");

    const summary = details.createEl("summary");
    summary.createSpan({ text: "오늘 타임라인" });

    const refresh = summary.createSpan({ cls: "memory-tool-section-action" });
    setIcon(refresh, "refresh-cw");
    refresh.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      void this.refreshToday();
    });

    this.todayList = details.createDiv({ cls: "memory-tool-today" });
  }

  /**
   * Show today's entries, newest last (the file's own order).
   *
   * Reads through the adapter and checks every known filename layout, so the
   * panel keeps working on a knowledge base that predates the current setting.
   */
  private async refreshToday(): Promise<void> {
    this.todayList.empty();

    const adapter = this.app.vault.adapter;
    let content: string | null = null;
    let found: string | null = null;

    for (const path of candidatePaths(this.host.basePrefix, new Date())) {
      if (await adapter.exists(path)) {
        content = await adapter.read(path);
        found = path;
        break;
      }
    }

    if (content === null) {
      this.todayList.createDiv({
        cls: "memory-tool-empty",
        text: "오늘 기록이 아직 없습니다.",
      });
      return;
    }

    const entries = content
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.startsWith("- "));

    if (entries.length === 0) {
      this.todayList.createDiv({ cls: "memory-tool-empty", text: "오늘 기록이 아직 없습니다." });
      return;
    }

    for (const entry of entries) {
      const row = this.todayList.createDiv({ cls: "memory-tool-entry" });
      const body = entry.slice(2);
      const split = body.indexOf(" | ");

      if (split > 0) {
        row.createSpan({ cls: "memory-tool-entry-time", text: body.slice(0, split) });
        row.createSpan({ cls: "memory-tool-entry-text", text: body.slice(split + 3) });
      } else {
        row.createSpan({ cls: "memory-tool-entry-text", text: body });
      }
    }

    if (found) {
      const open = this.todayList.createDiv({
        cls: "memory-tool-open-file",
        text: "파일 열기",
      });
      open.addEventListener("click", () => void this.openPath(found!));
    }
  }

  // --- Modules -------------------------------------------------------------

  private buildModules(root: HTMLElement): void {
    const details = root.createEl("details", { cls: "memory-tool-section" });
    details.setAttr("open", "");

    const summary = details.createEl("summary");
    summary.createSpan({ text: "모듈" });

    const refresh = summary.createSpan({ cls: "memory-tool-section-action" });
    setIcon(refresh, "refresh-cw");
    refresh.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      void this.refreshModules();
    });

    this.moduleFilter = details.createEl("input", {
      cls: "memory-tool-module-filter",
      attr: { type: "text", placeholder: "모듈 검색..." },
    });
    this.moduleFilter.addEventListener("input", () => this.renderModules());

    this.moduleList = details.createDiv({ cls: "memory-tool-modules" });
  }

  private async refreshModules(): Promise<void> {
    this.moduleList.empty();
    this.moduleList.createDiv({ cls: "memory-tool-empty", text: "불러오는 중..." });

    this.modules = await this.host.listModules();
    this.renderModules();
  }

  private renderModules(): void {
    this.moduleList.empty();

    const filter = this.moduleFilter.value.trim().toLowerCase();
    const shown = filter
      ? this.modules.filter((m) => m.toLowerCase().includes(filter))
      : this.modules;

    if (shown.length === 0) {
      this.moduleList.createDiv({
        cls: "memory-tool-empty",
        text: this.modules.length === 0 ? "모듈이 없습니다." : "일치하는 모듈이 없습니다.",
      });
      return;
    }

    for (const name of shown) {
      const row = this.moduleList.createDiv({ cls: "memory-tool-module", text: name });
      row.addEventListener("click", () => void this.openModule(name));
    }
  }

  private async openModule(name: string): Promise<void> {
    for (const path of moduleCandidatePaths(this.host.basePrefix, name)) {
      if (await this.openPath(path)) return;
    }
    new Notice(`'${name}' 을(를) 이 vault에서 찾지 못했습니다. Knowledge Base Folder 설정을 확인하세요.`, 8000);
  }

  /**
   * Open a vault-relative path in the main editor.
   *
   * Falls back to the adapter check because the knowledge base commonly lives in
   * a dot-folder, which Obsidian's file index skips -- getAbstractFileByPath
   * returns null there even though the file exists.
   */
  private async openPath(path: string): Promise<boolean> {
    const file = this.app.vault.getAbstractFileByPath(path);
    if (file instanceof TFile) {
      await this.app.workspace.getLeaf(false).openFile(file);
      return true;
    }
    return false;
  }

  // --- Actions -------------------------------------------------------------

  private buildActions(root: HTMLElement): void {
    const details = root.createEl("details", { cls: "memory-tool-section" });

    details.createEl("summary").createSpan({ text: "도구" });

    const body = details.createDiv({ cls: "memory-tool-actions" });

    // Everything in this section shells out to Python. On mobile there is none,
    // so the buttons are replaced by an explanation rather than offered and
    // failed — a disabled control the user cannot fix is just noise.
    if (!this.host.cliAvailable()) {
      body.createDiv({
        cls: "memory-tool-empty",
        text:
          "컨텍스트 생성·경로 점검·인덱스는 Python CLI 가 필요해 이 기기에서는 " +
          "쓸 수 없습니다. 기록은 정상 저장되며, 데스크톱에서 vault 를 열면 " +
          "검색 인덱스가 따라잡습니다.",
      });

      body.createDiv({
        cls: "memory-tool-base-note",
        text: `Base: ${describePrefix(this.host.basePrefix)}`,
      });
      return;
    }

    this.actionButton(body, "AI 컨텍스트 생성 (mcontext)", async () => {
      new Notice("컨텍스트 생성 중...");
      await this.host.cli.buildContext();
      new Notice("컨텍스트 생성 완료 (.claude/memory-context.md)");
    });

    this.actionButton(body, "모듈 경로 점검 (mcheck)", async () => {
      new Notice("경로 점검 중...");
      const res = await this.host.cli.checkHealth();
      new Notice(res || "점검 완료.");
    });

    this.actionButton(body, "검색 인덱스 동기화", async () => {
      const pending = this.host.pendingIndexCount();
      await this.host.syncIndex();
      new Notice(pending > 0 ? `인덱스 동기화 완료 (${pending}건 반영)` : "인덱스 동기화 완료");
    });

    body.createDiv({
      cls: "memory-tool-base-note",
      text: `Base: ${describePrefix(this.host.basePrefix)}`,
    });
  }

  private actionButton(parent: HTMLElement, label: string, run: () => Promise<void>): void {
    const btn = parent.createEl("button", { text: label });
    btn.addEventListener("click", async () => {
      btn.setAttr("disabled", "true");
      try {
        await run();
      } catch (err: any) {
        new Notice(`실패: ${err.message}`);
      } finally {
        btn.removeAttribute("disabled");
      }
    });
  }
}
