/**
 * The memory_tool side panel.
 *
 * One view with stacked, collapsible sections rather than several views: the
 * whole point is seeing capture, today's entries and module navigation at the
 * same time, and separate views would each claim their own tab and defeat that.
 *
 * "Module navigation" means a search box: the panel is narrow, and a standing
 * list of every module would be the tallest thing in it while being the part
 * that changes least.
 *
 * The capture box being permanently on screen is what makes the panel worth
 * having. A modal -- however fast -- costs a deliberate "open the thing" step
 * before any typing happens, and that step is the actual friction in a 0.5s
 * capture promise.
 */

import { ItemView, Notice, Platform, TFile, WorkspaceLeaf, setIcon } from "obsidian";
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
  /**
   * Advance the module the user is looking at by one growth level, falling
   * back to a picker when the open document is not a module.
   */
  growFromContext(): void;
}

export class MemoryPanelView extends ItemView {
  private host: PanelHost;

  private captureInput!: HTMLTextAreaElement;
  private todayList!: HTMLElement;
  private moduleList!: HTMLElement;
  private moduleFilter!: HTMLInputElement;
  private statusEl!: HTMLElement;

  /** Module list cache. null until something asks for it. */
  private modules: string[] | null = null;
  /** Guards against a second load while the first is in flight. */
  private loadingModules = false;

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
    // Header actions sit at the panel's top-right and are tappable, which is the
    // only kind of control that exists on a phone.
    this.addAction("pencil", "입력창으로 이동", () => this.focusCapture());
    this.addAction("refresh-cw", "새로 고침", () => {
      void this.refreshToday();
      void this.reloadModules();
    });

    const root = this.contentEl;
    root.empty();
    root.addClass("memory-tool-panel");

    this.buildCapture(root);
    this.buildToday(root);
    this.buildModules(root);
    this.buildActions(root);

    await this.refreshToday();
    // Draws the "type to search" hint; with an empty box it fetches nothing.
    void this.renderModules();
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

    // On a phone, Enter is the newline key and there is no Shift to hold, so
    // Enter-to-submit would make multi-line capture impossible and single-line
    // capture surprising. The button is the primary control there; on desktop it
    // sits alongside the Enter shortcut.
    const submitOnEnter = !Platform.isMobile;

    this.captureInput = section.createEl("textarea", {
      cls: "memory-tool-capture-input",
      attr: {
        rows: submitOnEnter ? "2" : "3",
        placeholder: submitOnEnter
          ? "지금 무엇을 하고 있나요?  Enter로 기록, Shift+Enter 줄바꿈"
          : "지금 무엇을 하고 있나요?",
      },
    });

    const row = section.createDiv({ cls: "memory-tool-capture-row" });
    this.statusEl = row.createDiv({ cls: "memory-tool-capture-status" });

    const submitBtn = row.createEl("button", {
      cls: "mod-cta memory-tool-capture-send",
      text: "기록",
    });
    submitBtn.addEventListener("click", () => void this.submitCapture());

    this.captureInput.addEventListener("keydown", (e: KeyboardEvent) => {
      // isComposing is essential, not defensive: with a Korean IME the Enter that
      // commits a composition fires keydown too, so without this guard the entry
      // is submitted mid-syllable and the last character is lost.
      if (e.isComposing || e.keyCode === 229) return;

      if (submitOnEnter && e.key === "Enter" && !e.shiftKey) {
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

  /**
   * The module section is a search box, not a listing.
   *
   * A full list of every module is dozens of rows of noise in a sidebar this
   * narrow, and it pushes today's timeline -- the part that changes -- off the
   * screen. Nothing is drawn until there is a query to answer, which also means
   * the list is not fetched when the panel merely opens; on desktop that fetch
   * starts a Python process.
   */
  private buildModules(root: HTMLElement): void {
    const details = root.createEl("details", { cls: "memory-tool-section" });
    details.setAttr("open", "");

    const summary = details.createEl("summary");
    summary.createSpan({ text: "모듈 검색" });

    const refresh = summary.createSpan({ cls: "memory-tool-section-action" });
    setIcon(refresh, "refresh-cw");
    refresh.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      void this.reloadModules();
    });

    this.moduleFilter = details.createEl("input", {
      cls: "memory-tool-module-filter",
      attr: { type: "text", placeholder: "모듈 이름 검색..." },
    });
    this.moduleFilter.addEventListener("input", () => void this.renderModules());

    this.moduleList = details.createDiv({ cls: "memory-tool-modules" });
  }

  /** Drop the cache and fetch again, then redraw whatever is on screen. */
  private async reloadModules(): Promise<void> {
    this.modules = null;
    await this.renderModules();
  }

  /**
   * Load the module list once and keep it.
   *
   * Returns null while another call is already loading, so a fast typist does
   * not start several CLI calls for the same list.
   */
  private async loadModules(): Promise<string[] | null> {
    if (this.modules !== null) return this.modules;
    if (this.loadingModules) return null;

    this.loadingModules = true;
    try {
      this.modules = await this.host.listModules();
      return this.modules;
    } finally {
      this.loadingModules = false;
    }
  }

  private async renderModules(): Promise<void> {
    const filter = this.moduleFilter.value.trim().toLowerCase();

    if (!filter) {
      this.moduleList.empty();
      this.moduleList.createDiv({
        cls: "memory-tool-empty",
        text: "검색어를 입력하면 모듈이 나타납니다.",
      });
      return;
    }

    if (this.modules === null) {
      this.moduleList.empty();
      this.moduleList.createDiv({ cls: "memory-tool-empty", text: "불러오는 중..." });

      const loaded = await this.loadModules();
      // Another call is loading, or the query changed while we waited; that
      // call's own render will draw the result.
      if (loaded === null) return;
      if (this.moduleFilter.value.trim().toLowerCase() !== filter) {
        void this.renderModules();
        return;
      }
    }

    const all = this.modules ?? [];
    const shown = all.filter((m) => m.toLowerCase().includes(filter));

    this.moduleList.empty();

    if (shown.length === 0) {
      this.moduleList.createDiv({
        cls: "memory-tool-empty",
        text: all.length === 0 ? "모듈이 없습니다." : "일치하는 모듈이 없습니다.",
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

    // Placed with the tools rather than beside each search result: growing is
    // something you do to the note in front of you, not something you pick a
    // target for. The host falls back to a picker when nothing suitable is open.
    this.actionButton(body, "모듈 한 단계 키우기 (mmodule grow)", async () => {
      this.host.growFromContext();
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
