import { Plugin, Notice, PluginSettingTab, Setting, App } from "obsidian";
import { MemoryToolCli } from "./cli/memoryToolCli";
import { RecordModal } from "./modals/RecordModal";
import { CreateModuleModal } from "./modals/CreateModuleModal";
import { ModuleSuggestModal } from "./modals/ModuleSuggestModal";
import { AskModal } from "./modals/AskModal";
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
}

const DEFAULT_SETTINGS: MemoryToolSettings = {
  pythonPath: "python",
  baseFolder: "",
};

export default class MemoryToolPlugin extends Plugin {
  settings: MemoryToolSettings = DEFAULT_SETTINGS;
  cli: MemoryToolCli = new MemoryToolCli();

  /**
   * Knowledge base location as a vault-relative prefix.
   * "" means the vault root itself is the base folder.
   */
  basePrefix: string = DEFAULT_BASE;

  /** Absolute path of the vault root. */
  vaultRoot: string = "";

  async onload() {
    await this.loadSettings();

    // Get current vault root path
    // @ts-ignore
    this.vaultRoot = this.app.vault.adapter.getBasePath ? this.app.vault.adapter.getBasePath() : "";
    this.cli.setCwd(this.vaultRoot);
    this.cli.setPythonPath(this.settings.pythonPath);

    await this.resolveBaseFolder();

    // 1. Ribbon Icon: Quick Timeline Record
    this.addRibbonIcon("clock", "Quick Timeline Record (memory_tool)", () => {
      new RecordModal(this.app, this.cli).open();
    });

    // 2. Ribbon Icon: Build AI Context
    this.addRibbonIcon("brain", "Build AI Context (mcontext)", async () => {
      new Notice("Building AI Context...");
      try {
        await this.cli.buildContext();
        new Notice("OK AI Context built (.claude/memory-context.md)");
      } catch (err: any) {
        new Notice(`Failed to build context: ${err.message}`);
      }
    });

    // 2b. Ribbon Icon: Ask Your Memory
    this.addRibbonIcon("help-circle", "Ask Your Memory (mask)", () => {
      new AskModal(this.app, this.cli, () => this.basePrefix).open();
    });

    // 3. Command: Quick Record Timeline (Hotkey: Ctrl+Alt+M)
    this.addCommand({
      id: "record-timeline",
      name: "Record Timeline Entry (0.5s)",
      hotkeys: [{ modifiers: ["Mod", "Alt"], key: "m" }],
      callback: () => {
        new RecordModal(this.app, this.cli).open();
      },
    });

    // 4. Command: Create Module
    this.addCommand({
      id: "create-module",
      name: "Create Module",
      callback: () => {
        new CreateModuleModal(this.app, this.cli, () => this.basePrefix).open();
      },
    });

    // 5. Command: Go to Module (Hotkey: Ctrl+Alt+G)
    this.addCommand({
      id: "go-to-module",
      name: "Go to Module",
      hotkeys: [{ modifiers: ["Mod", "Alt"], key: "g" }],
      callback: () => {
        new ModuleSuggestModal(this.app, this.cli, () => this.basePrefix).open();
      },
    });

    // 6. Command: Build AI Context
    this.addCommand({
      id: "build-context",
      name: "Build AI Context (mcontext)",
      callback: async () => {
        new Notice("Building AI Context...");
        try {
          await this.cli.buildContext();
          new Notice("OK AI Context built (.claude/memory-context.md)");
        } catch (err: any) {
          new Notice(`Failed to build context: ${err.message}`);
        }
      },
    });

    // 7. Command: Check Module Path Health
    this.addCommand({
      id: "check-path-health",
      name: "Check Module Path Health (mcheck)",
      callback: async () => {
        new Notice("Checking module path health...");
        try {
          const res = await this.cli.checkHealth();
          new Notice(res || "Path check complete.");
        } catch (err: any) {
          new Notice(`Health check failed: ${err.message}`);
        }
      },
    });

    // 8. Command: Ask Your Memory (Hotkey: Ctrl+Alt+A)
    this.addCommand({
      id: "ask-memory",
      name: "Ask Your Memory (mask)",
      hotkeys: [{ modifiers: ["Mod", "Alt"], key: "a" }],
      callback: () => {
        new AskModal(this.app, this.cli, () => this.basePrefix).open();
      },
    });

    // 9. Command: Show resolved base folder
    this.addCommand({
      id: "show-base-folder",
      name: "Show Knowledge Base Folder (mbase)",
      callback: async () => {
        await this.resolveBaseFolder();
        new Notice(`Knowledge base folder: ${describePrefix(this.basePrefix)}`);
      },
    });

    // Settings Tab
    this.addSettingTab(new MemoryToolSettingTab(this.app, this));
  }

  onunload() {}

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

    let info;
    try {
      info = await this.cli.getBaseInfo();
    } catch (err: any) {
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

    containerEl.createEl("h2", { text: "Memory Tool Integration Settings" });

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

    containerEl.createEl("p", {
      text:
        "To change where memory_tool itself stores the knowledge base, run " +
        "'mbase set <name>' in the vault folder. This setting only tells the " +
        "plugin where to look.",
      cls: "setting-item-description",
    });
  }
}
