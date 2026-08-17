import { Plugin, Notice, PluginSettingTab, Setting, App, WorkspaceLeaf } from "obsidian";
import { MemoryToolCli } from "./cli/memoryToolCli";
import { RecordModal } from "./modals/RecordModal";
import { CreateModuleModal } from "./modals/CreateModuleModal";
import { ModuleSuggestModal } from "./modals/ModuleSuggestModal";
import { AskModal } from "./modals/AskModal";
import { MEMORY_PANEL_VIEW, MemoryPanelView, PanelHost } from "./views/MemoryPanelView";
import { recordDirect } from "./timeline/directWriter";
import { asScanAdapter, listModules, probeBasePrefix } from "./vaultScan";
import {
  DEFAULT_BASE,
  describePrefix,
  normalizePrefix,
  vaultRelativeBase,
} from "./paths";

interface MemoryToolSettings {
  pythonPath: string;
  /** Base folder override, relative to the vault root. Empty = auto-detect. */
  baseFolder: string;
  /**
   * Append timeline entries directly instead of shelling out to Python.
   * On by default: the CLI path costs ~1.6s of interpreter start per entry.
   */
  directCapture: boolean;
  /** Auto-run the indexer once this many direct writes are unindexed. 0 = never. */
  indexSyncThreshold: number;
  /** Direct writes not yet reflected in the SQLite search index. */
  pendingIndex: number;
}

const DEFAULT_SETTINGS: MemoryToolSettings = {
  pythonPath: "python",
  baseFolder: "",
  directCapture: true,
  indexSyncThreshold: 10,
  pendingIndex: 0,
};

export default class MemoryToolPlugin extends Plugin implements PanelHost {
  settings: MemoryToolSettings = DEFAULT_SETTINGS;
  cli: MemoryToolCli = new MemoryToolCli();

  /**
   * Knowledge base location as a vault-relative prefix.
   * "" means the vault root itself is the base folder.
   */
  basePrefix: string = DEFAULT_BASE;

  /** Absolute path of the vault root. */
  vaultRoot: string = "";

  /** Guards against two index syncs overlapping. */
  private syncing = false;

  async onload() {
    await this.loadSettings();

    // @ts-ignore -- getBasePath exists on the desktop adapter only
    this.vaultRoot = this.app.vault.adapter.getBasePath ? this.app.vault.adapter.getBasePath() : "";
    this.cli.setCwd(this.vaultRoot);
    this.cli.setPythonPath(this.settings.pythonPath);

    await this.resolveBaseFolder();

    this.registerView(MEMORY_PANEL_VIEW, (leaf) => new MemoryPanelView(leaf, this));

    // Ribbon: one entry point now that the panel holds everything.
    this.addRibbonIcon("clock", "Memory Tool 패널 열기", () => {
      void this.activatePanel();
    });

    // Hotkeys avoid Ctrl+Alt on purpose. On Windows that combination is AltGr,
    // which IMEs (Korean among them) and other apps' global shortcuts intercept
    // before Obsidian ever sees the key -- the binding shows up correctly in the
    // settings list and simply never fires.
    this.addCommand({
      id: "open-panel",
      name: "Memory Tool 패널 열기",
      hotkeys: [{ modifiers: ["Mod", "Shift"], key: "m" }],
      callback: () => {
        void this.activatePanel();
      },
    });

    this.addCommand({
      id: "record-timeline",
      name: "타임라인 기록 (빠른 입력)",
      hotkeys: [{ modifiers: ["Mod", "Shift"], key: "j" }],
      callback: () => {
        new RecordModal(this.app, (msg) => this.recordEntry(msg)).open();
      },
    });

    // Module navigation works everywhere: the list falls back to a vault scan.
    this.addCommand({
      id: "go-to-module",
      name: "모듈로 이동",
      hotkeys: [{ modifiers: ["Mod", "Shift"], key: "g" }],
      callback: () => {
        new ModuleSuggestModal(
          this.app,
          () => this.listModules(),
          () => this.basePrefix
        ).open();
      },
    });

    this.addCommand({
      id: "show-base-folder",
      name: "지식 베이스 폴더 확인 (mbase)",
      callback: async () => {
        await this.resolveBaseFolder();
        new Notice(`Knowledge base folder: ${describePrefix(this.basePrefix)}`);
      },
    });

    // The rest shell out to Python. They are not registered on mobile at all --
    // a palette entry that can only ever report "not available here" is worse
    // than its absence.
    if (this.cli.isAvailable()) {
      this.registerCliCommands();
    }

    this.addSettingTab(new MemoryToolSettingTab(this.app, this));

    // Entries written directly in an earlier session are still unindexed.
    if (this.settings.pendingIndex > 0 && this.cli.isAvailable()) {
      this.app.workspace.onLayoutReady(() => void this.syncIndex().catch(() => {}));
    }
  }

  /** Commands that require the Python CLI; desktop only. */
  private registerCliCommands(): void {
    this.addCommand({
      id: "create-module",
      name: "모듈 생성",
      callback: () => {
        new CreateModuleModal(this.app, this.cli, () => this.basePrefix).open();
      },
    });

    this.addCommand({
      id: "build-context",
      name: "AI 컨텍스트 생성 (mcontext)",
      callback: async () => {
        new Notice("컨텍스트 생성 중...");
        try {
          await this.cli.buildContext();
          new Notice("컨텍스트 생성 완료 (.claude/memory-context.md)");
        } catch (err: any) {
          new Notice(`컨텍스트 생성 실패: ${err.message}`);
        }
      },
    });

    this.addCommand({
      id: "check-path-health",
      name: "모듈 경로 점검 (mcheck)",
      callback: async () => {
        new Notice("경로 점검 중...");
        try {
          new Notice((await this.cli.checkHealth()) || "점검 완료.");
        } catch (err: any) {
          new Notice(`점검 실패: ${err.message}`);
        }
      },
    });

    this.addCommand({
      id: "ask-memory",
      name: "기억에 질문하기 (mask)",
      callback: () => {
        new AskModal(this.app, this.cli, () => this.basePrefix).open();
      },
    });

    this.addCommand({
      id: "sync-index",
      name: "검색 인덱스 동기화",
      callback: async () => {
        const pending = this.settings.pendingIndex;
        try {
          await this.syncIndex();
          new Notice(pending > 0 ? `인덱스 동기화 완료 (${pending}건)` : "인덱스 동기화 완료");
        } catch (err: any) {
          new Notice(`인덱스 동기화 실패: ${err.message}`);
        }
      },
    });

  }

  onunload() {}

  /** Reveal the side panel, creating it in the right sidebar if needed. */
  async activatePanel(): Promise<void> {
    const { workspace } = this.app;

    let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(MEMORY_PANEL_VIEW)[0] ?? null;

    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      if (!leaf) return;
      await leaf.setViewState({ type: MEMORY_PANEL_VIEW, active: true });
    }

    await workspace.revealLeaf(leaf);

    const view = leaf.view;
    if (view instanceof MemoryPanelView) view.focusCapture();
  }

  // --- PanelHost -----------------------------------------------------------

  /**
   * Record one timeline entry.
   *
   * Direct write is the default because the CLI round-trip is dominated by
   * Python start-up (~1.6s measured) rather than by the work itself. The CLI
   * path stays available for anyone who would rather have the indexer run
   * inline, and is used automatically as a fallback if the direct write fails.
   */
  async recordEntry(message: string): Promise<{ path: string; entry: string }> {
    if (!this.settings.directCapture) {
      await this.cli.recordTimeline(message);
      return { path: "", entry: message };
    }

    try {
      const result = await recordDirect(this.app.vault.adapter, this.basePrefix, message);

      this.settings.pendingIndex += 1;
      await this.saveData(this.settings);

      const threshold = this.settings.indexSyncThreshold;
      if (threshold > 0 && this.settings.pendingIndex >= threshold) {
        void this.syncIndex().catch(() => {
          // Indexing is best-effort; the entry itself is already on disk.
        });
      }

      return { path: result.path, entry: result.entry };
    } catch (err: any) {
      // The direct path is the optimization, not the contract. If it fails --
      // permissions, an unexpected base folder -- fall back rather than lose
      // the entry, and say which path actually took it.
      await this.cli.recordTimeline(message);
      new Notice(`직접 기록 실패로 CLI로 기록했습니다: ${err.message}`, 8000);
      return { path: "", entry: message };
    }
  }

  pendingIndexCount(): number {
    return this.settings.pendingIndex;
  }

  /** Whether CLI-backed features can run (false on mobile). */
  cliAvailable(): boolean {
    return this.cli.isAvailable();
  }

  /**
   * List modules, preferring the CLI and falling back to a vault scan.
   *
   * The scan mirrors the CLI's discovery rules, so mobile gets the same list
   * without Python. It is the fallback rather than the default because the CLI
   * remains the definition of what counts as a module.
   */
  async listModules(): Promise<string[]> {
    if (this.cli.isAvailable()) {
      const fromCli = await this.cli.listModules();
      if (fromCli.length > 0) return fromCli;
    }
    return listModules(asScanAdapter(this.app.vault.adapter), this.basePrefix);
  }

  /**
   * Bring the SQLite search index up to date with directly-written entries.
   *
   * On mobile this is a no-op: the index is a desktop artifact and the pending
   * count is deliberately preserved, so the entries written on the phone are
   * indexed the next time the vault is opened on a machine that can.
   */
  async syncIndex(): Promise<void> {
    if (!this.cli.isAvailable()) return;
    if (this.syncing) return;
    this.syncing = true;
    try {
      await this.cli.syncIndex();
      this.settings.pendingIndex = 0;
      await this.saveData(this.settings);
    } finally {
      this.syncing = false;
    }
  }

  // --- Base folder ---------------------------------------------------------

  /**
   * Determine where the knowledge base sits *relative to the vault root*.
   *
   * memory_tool reports the base folder relative to the project root, which is
   * not the same reference point: when the vault is the base folder itself, the
   * correct prefix is "" even though memory_tool reports ".memory". Using the
   * name directly produced .memory/.memory/... and silently found nothing.
   * Working from the absolute path avoids that entirely.
   *
   * A manual override wins. Detection failure is not fatal -- the plugin falls
   * back to the historical default so its other commands keep working.
   */
  async resolveBaseFolder(): Promise<void> {
    const override = this.settings.baseFolder.trim();
    if (override) {
      this.basePrefix = normalizePrefix(override);
      return;
    }

    // Without the CLI (mobile), find the base by looking for its marker folders
    // instead of asking memory_tool where it put them.
    if (!this.cli.isAvailable()) {
      const probed = await probeBasePrefix(asScanAdapter(this.app.vault.adapter));
      if (probed !== null) {
        this.basePrefix = probed;
      } else {
        this.basePrefix = DEFAULT_BASE;
        new Notice(
          "memory_tool: 이 vault 안에서 지식 베이스를 찾지 못했습니다 " +
            "(timeline/ 과 modules/ 를 가진 폴더). 설정에서 직접 지정하세요.",
          10000
        );
      }
      return;
    }

    let info;
    try {
      info = await this.cli.getBaseInfo();
    } catch {
      this.basePrefix = DEFAULT_BASE;
      new Notice(
        "memory_tool: could not detect the knowledge base folder, assuming " +
          `${DEFAULT_BASE}/. Set it manually in the plugin settings if that is wrong.`
      );
      return;
    }

    const prefix = vaultRelativeBase(this.vaultRoot, info.base);

    if (prefix === null) {
      // The base folder is not inside this vault, so Obsidian cannot open its
      // files at all. Say so plainly rather than silently failing later.
      this.basePrefix = DEFAULT_BASE;
      new Notice(
        `memory_tool: the knowledge base (${info.base}) is outside this vault, ` +
          "so its files cannot be opened here. Open that folder as the vault, or " +
          "set the folder manually in the plugin settings.",
        10000
      );
      return;
    }

    this.basePrefix = prefix;

    if (info.source === "nested-artifact") {
      new Notice(
        "memory_tool: a leftover nested .memory/ folder was found and ignored. " +
          "Entries recorded there by older versions are not visible in normal " +
          "commands -- run 'mbase show' for details.",
        10000
      );
    }
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
    this.cli.setPythonPath(this.settings.pythonPath);
    await this.resolveBaseFolder();
  }
}

class MemoryToolSettingTab extends PluginSettingTab {
  plugin: MemoryToolPlugin;

  constructor(app: App, plugin: MemoryToolPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName("Python Executable Path")
      .setDesc("Path to Python executable or virtual environment (default: 'python')")
      .addText((text) =>
        text
          .setPlaceholder("python")
          .setValue(this.plugin.settings.pythonPath)
          .onChange(async (value) => {
            this.plugin.settings.pythonPath = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Knowledge Base Folder")
      .setDesc(
        `Folder holding timeline/ and modules/, relative to the vault root. ` +
          `Leave empty to detect it automatically (currently: ` +
          `${describePrefix(this.plugin.basePrefix)}). Use "." when the vault root ` +
          `itself is the knowledge base — which is the case if you opened the ` +
          `.memory folder as your vault.`
      )
      .addText((text) =>
        text
          .setPlaceholder("(auto-detect)")
          .setValue(this.plugin.settings.baseFolder)
          .onChange(async (value) => {
            this.plugin.settings.baseFolder = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl).setName("캡처").setHeading();

    new Setting(containerEl)
      .setName("Python 없이 직접 기록")
      .setDesc(
        "타임라인 항목을 플러그인이 직접 파일에 씁니다. CLI 경유는 항목당 " +
          "Python 시작 비용(약 1.6초)이 붙습니다. 끄면 항상 CLI를 씁니다."
      )
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.directCapture).onChange(async (value) => {
          this.plugin.settings.directCapture = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("인덱스 자동 동기화 기준")
      .setDesc(
        "직접 기록이 이 개수만큼 쌓이면 검색 인덱스를 자동으로 갱신합니다. " +
          `0이면 수동으로만 갱신합니다. 현재 미반영: ${this.plugin.settings.pendingIndex}건.`
      )
      .addText((text) =>
        text
          .setPlaceholder("10")
          .setValue(String(this.plugin.settings.indexSyncThreshold))
          .onChange(async (value) => {
            const parsed = Number.parseInt(value, 10);
            this.plugin.settings.indexSyncThreshold =
              Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
            await this.plugin.saveSettings();
          })
      );

    containerEl.createEl("p", {
      text:
        "단축키가 반응하지 않으면 설정 → 단축키에서 해당 명령의 기존 " +
        "Ctrl+Alt 조합을 지우고 다시 지정하세요. Windows에서 Ctrl+Alt는 AltGr로 " +
        "해석되어 한글 IME나 다른 앱의 전역 단축키가 먼저 가로챕니다.",
      cls: "setting-item-description",
    });

    containerEl.createEl("p", {
      text:
        "To change where memory_tool itself stores the knowledge base, run " +
        "'mbase set <name>' in the vault folder. This setting only tells the " +
        "plugin where to look.",
      cls: "setting-item-description",
    });
  }
}
