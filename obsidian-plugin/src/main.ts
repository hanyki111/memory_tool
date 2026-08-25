import { Plugin, Notice, PluginSettingTab, Setting, App, WorkspaceLeaf } from "obsidian";
import { MemoryToolCli } from "./cli/memoryToolCli";
import { RecordModal } from "./modals/RecordModal";
import { CreateModuleModal } from "./modals/CreateModuleModal";
import { ModuleSuggestModal } from "./modals/ModuleSuggestModal";
import { AskModal } from "./modals/AskModal";
import { MEMORY_PANEL_VIEW, MemoryPanelView, PanelHost } from "./views/MemoryPanelView";
import {
  FilenameLayoutSetting,
  filenameFor,
  recordDirect,
  resolveFilenameLayout,
} from "./timeline/directWriter";
import { asScanAdapter, listModules, probeBasePrefix } from "./vaultScan";
import {
  DEFAULT_BASE,
  describePrefix,
  moduleNameFromPath,
  modulePrefixFromFolder,
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
  /**
   * Timeline filename layout for files this plugin creates.
   * "auto" follows config.yaml, then the names already in use.
   */
  filenameLayout: FilenameLayoutSetting;
  /** Auto-run the indexer once this many direct writes are unindexed. 0 = never. */
  indexSyncThreshold: number;
  /** Direct writes not yet reflected in the SQLite search index. */
  pendingIndex: number;
}

const DEFAULT_SETTINGS: MemoryToolSettings = {
  pythonPath: "python",
  baseFolder: "",
  directCapture: true,
  filenameLayout: "auto",
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

    // Two ribbon entry points, both reachable by tap alone. On a phone there is
    // no modifier key to press, so every action must have a button somewhere.
    this.ribbonButton("pencil", "타임라인 기록 (m)", () => {
      new RecordModal(this.app, (msg) => this.recordEntry(msg)).open();
    });

    this.ribbonButton("clock", "Memory Tool 패널 열기", () => {
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
      id: "show-filename-layout",
      name: "타임라인 파일명 규칙 확인",
      callback: async () => {
        const resolved = await resolveFilenameLayout(
          this.app.vault.adapter,
          this.basePrefix,
          new Date(),
          this.settings.filenameLayout
        );
        const sources: Record<string, string> = {
          setting: "플러그인 설정",
          config: "config.yaml",
          files: "기존 타임라인 파일명",
          default: "기본값",
        };
        new Notice(
          `오늘 새 파일을 만들면: ${filenameFor(new Date(), resolved.layout)}\n` +
            `근거: ${sources[resolved.source]} · Base: ${describePrefix(this.basePrefix)}`,
          10000
        );
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
      this.registerFolderMenu();
    }

    this.addSettingTab(new MemoryToolSettingTab(this.app, this));

    // Entries written directly in an earlier session are still unindexed.
    if (this.settings.pendingIndex > 0 && this.cli.isAvailable()) {
      this.app.workspace.onLayoutReady(() => void this.syncIndex().catch(() => {}));
    }
  }

  /**
   * "여기에 모듈 생성" on a folder inside the modules tree.
   *
   * Typing the parent path by hand is the part of module creation that is both
   * tedious and easy to get wrong, and the file explorer already knows it.
   * Folders outside `<base>/modules` get no entry: modules cannot live there,
   * so offering it would only produce an error later.
   */
  private registerFolderMenu(): void {
    this.registerEvent(
      this.app.workspace.on("file-menu", (menu, file) => {
        // A folder has children; a note does not. Checking for the property
        // avoids importing TFolder just for an instanceof.
        if (!("children" in file)) return;

        const prefix = modulePrefixFromFolder(this.basePrefix, file.path);
        if (prefix === null) return;

        menu.addItem((item) => {
          item
            .setTitle("여기에 모듈 생성")
            .setIcon("folder-plus")
            .onClick(() => {
              new CreateModuleModal(
                this.app,
                this.cli,
                () => this.basePrefix,
                prefix
              ).open();
            });
        });
      })
    );
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
      id: "grow-module",
      name: "모듈 한 단계 키우기 (mmodule grow)",
      callback: () => {
        // The moment a seed feels too small is the moment you are looking at
        // it, so the open document is the default target and picking from a
        // list is only the fallback.
        const open = this.app.workspace.getActiveFile();
        const name = open
          ? moduleNameFromPath(this.basePrefix, open.path)
          : null;

        if (name) {
          void this.growModule(name);
          return;
        }

        new Notice("열린 문서가 모듈이 아닙니다. 목록에서 고르세요.");
        new ModuleSuggestModal(
          this.app,
          () => this.listModules(),
          () => this.basePrefix,
          (chosen) => void this.growModule(chosen)
        ).open();
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

  /**
   * Add a ribbon button that cannot fail silently.
   *
   * Two failure modes are covered, both of which look identical to the user --
   * "the button does nothing":
   *
   *   1. An icon name Obsidian does not know renders no SVG, leaving a blank
   *      strip of ribbon that is easy to miss and easy to mis-click. If nothing
   *      was drawn, a visible label is written into the button instead.
   *   2. An exception thrown inside the callback is swallowed by the event
   *      dispatcher, so the click appears to do nothing at all. Reporting it as
   *      a notice is the difference between a bug and a mystery.
   */
  private ribbonButton(icon: string, title: string, action: () => void): void {
    const el = this.addRibbonIcon(icon, title, () => {
      try {
        action();
      } catch (err: any) {
        console.error("[memory_tool] ribbon action failed", err);
        new Notice(`${title} 실패: ${err?.message ?? err}`, 10000);
      }
    });

    if (!el.querySelector("svg")) {
      el.addClass("memory-tool-ribbon-fallback");
      el.setText(title.slice(0, 2));
    }
  }

  /** Reveal the side panel, creating it in the right sidebar if needed. */
  async activatePanel(): Promise<void> {
    const { workspace } = this.app;

    try {
      let leaf: WorkspaceLeaf | null = workspace.getLeavesOfType(MEMORY_PANEL_VIEW)[0] ?? null;

      if (!leaf) {
        // Falling back to a new leaf matters on mobile, where the right sidebar
        // may not exist as a separate dock; returning early here used to make the
        // button do nothing at all, with no way to tell why.
        leaf = workspace.getRightLeaf(false) ?? workspace.getLeaf(true);
        if (!leaf) {
          new Notice("패널을 열 자리를 찾지 못했습니다.");
          return;
        }
        await leaf.setViewState({ type: MEMORY_PANEL_VIEW, active: true });
      }

      await workspace.revealLeaf(leaf);

      const view = leaf.view;
      if (view instanceof MemoryPanelView) view.focusCapture();
    } catch (err: any) {
      console.error("[memory_tool] failed to open the panel", err);
      new Notice(`패널 열기 실패: ${err?.message ?? err}`, 10000);
    }
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
      const result = await recordDirect(this.app.vault.adapter, this.basePrefix, message, {
        layoutSetting: this.settings.filenameLayout,
      });

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
  /**
   * Append the skeleton sections a module does not have yet.
   *
   * Reports the section names rather than a bare success: the point of the
   * command is that something was added, and "nothing to add" is a real and
   * unremarkable outcome that should not read as a failure.
   */
  async growModule(name: string): Promise<void> {
    new Notice(`'${name}' 다음 단계로...`);
    try {
      const output = await this.cli.growModule(name);

      // grow reports the rung it moved between; that transition is the whole
      // point of the command, so it is what the notice shows.
      const step = /(\d)\/(\d) \(([^)]+)\) -> (\d)\/\d \(([^)]+)\)/.exec(output);
      const already = /already at level (\d)\/(\d) \(([^)]+)\)/.exec(output);

      if (step) {
        new Notice(
          `${name}: ${step[1]}단계 ${step[3]} → ${step[4]}단계 ${step[5]}`,
          6000
        );
      } else if (already) {
        new Notice(
          `${name}: 이미 ${already[1]}/${already[2]}단계 (${already[3]}). 바뀐 것이 없습니다.`,
          6000
        );
      } else {
        new Notice(`${name}: 골격을 확장했습니다.`, 6000);
      }
    } catch (err: any) {
      new Notice(`골격 확장 실패: ${err.message}`, 8000);
    }
  }

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
      if (!(await this.useProbedBase())) {
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
      // The CLI is the definition of where the base is, but a failed call is no
      // reason to guess: the vault can still be searched for the marker folders,
      // and guessing wrong sends capture into a folder no command ever reads.
      if (!(await this.useProbedBase())) {
        new Notice(
          "memory_tool: could not detect the knowledge base folder, assuming " +
            `${DEFAULT_BASE}/. Set it manually in the plugin settings if that is wrong.`
        );
      }
      return;
    }

    const prefix = vaultRelativeBase(this.vaultRoot, info.base);

    if (prefix === null) {
      // The base folder is not inside this vault, so Obsidian cannot open its
      // files at all -- which happens routinely when a project's config points
      // its knowledge base at another project. A knowledge base that *is* in
      // this vault is the more useful answer, so look for one before giving up.
      const probed = await this.useProbedBase();
      new Notice(
        `memory_tool: the knowledge base (${info.base}) is outside this vault. ` +
          (probed
            ? `Using ${describePrefix(this.basePrefix)} in this vault instead.`
            : "Its files cannot be opened here. Open that folder as the vault, or " +
              "set the folder manually in the plugin settings."),
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

  /**
   * Fall back to searching the vault for the knowledge base.
   *
   * Sets `basePrefix` to the historical default when nothing is found, so the
   * caller only has to decide what to say. Returns whether a base was actually
   * located.
   */
  private async useProbedBase(): Promise<boolean> {
    const probed = await probeBasePrefix(asScanAdapter(this.app.vault.adapter));
    this.basePrefix = probed ?? DEFAULT_BASE;
    return probed !== null;
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

    // The layout matters beyond taste: Obsidian's Calendar and Periodic Notes
    // plugins find a daily note by its basename alone, so "20.md" is invisible
    // to them. The resolved value is shown because the interesting case is a
    // knowledge base whose config.yaml the plugin could not read.
    const layoutSetting = new Setting(containerEl)
      .setName("타임라인 파일명")
      .setDesc("확인 중...")
      .addDropdown((drop) =>
        drop
          .addOption("auto", "자동 (config.yaml → 기존 파일명)")
          .addOption("date", "2026-08-20.md (date)")
          .addOption("day", "20.md (day)")
          .setValue(this.plugin.settings.filenameLayout)
          .onChange(async (value) => {
            this.plugin.settings.filenameLayout = value as FilenameLayoutSetting;
            await this.plugin.saveSettings();
            void describeLayout();
          })
      );

    const describeLayout = async (): Promise<void> => {
      const resolved = await resolveFilenameLayout(
        this.app.vault.adapter,
        this.plugin.basePrefix,
        new Date(),
        this.plugin.settings.filenameLayout
      );
      const sources: Record<string, string> = {
        setting: "이 설정",
        config: "config.yaml",
        files: "기존 타임라인 파일명",
        default: "기본값",
      };
      layoutSetting.setDesc(
        `새 파일을 만들 때 쓰는 이름입니다. 지금 기준으로는 ` +
          `${filenameFor(new Date(), resolved.layout)} 로 만들어지며, ` +
          `근거는 ${sources[resolved.source]} 입니다.`
      );
    };

    void describeLayout();

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
