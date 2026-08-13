import { Plugin, Notice, PluginSettingTab, Setting, App } from "obsidian";
import { MemoryToolCli } from "./cli/memoryToolCli";
import { RecordModal } from "./modals/RecordModal";
import { CreateModuleModal } from "./modals/CreateModuleModal";
import { ModuleSuggestModal } from "./modals/ModuleSuggestModal";
import { DEFAULT_BASE, ROOT_BASE } from "./paths";

interface MemoryToolSettings {
  pythonPath: string;
  /** Base folder override. Empty means auto-detect from memory_tool. */
  baseFolder: string;
}

const DEFAULT_SETTINGS: MemoryToolSettings = {
  pythonPath: "python",
  baseFolder: "",
};

export default class MemoryToolPlugin extends Plugin {
  settings: MemoryToolSettings = DEFAULT_SETTINGS;
  cli: MemoryToolCli = new MemoryToolCli();

  /** Resolved base folder name, relative to the vault root ("." = vault root). */
  baseName: string = DEFAULT_BASE;

  async onload() {
    await this.loadSettings();

    // Get current vault root path
    // @ts-ignore
    const basePath = this.app.vault.adapter.getBasePath ? this.app.vault.adapter.getBasePath() : "";
    this.cli.setCwd(basePath);
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
        new CreateModuleModal(this.app, this.cli, () => this.baseName).open();
      },
    });

    // 5. Command: Go to Module (Hotkey: Ctrl+Alt+G)
    this.addCommand({
      id: "go-to-module",
      name: "Go to Module",
      hotkeys: [{ modifiers: ["Mod", "Alt"], key: "g" }],
      callback: () => {
        new ModuleSuggestModal(this.app, this.cli, () => this.baseName).open();
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

    // 8. Command: Show resolved base folder
    this.addCommand({
      id: "show-base-folder",
      name: "Show Knowledge Base Folder (mbase)",
      callback: async () => {
        await this.resolveBaseFolder();
        const where =
          this.baseName === ROOT_BASE ? "the vault root" : `${this.baseName}/`;
        new Notice(`Knowledge base folder: ${where}`);
      },
    });

    // Settings Tab
    this.addSettingTab(new MemoryToolSettingTab(this.app, this));
  }

  onunload() {}

  /**
   * Determine which vault folder holds the knowledge base.
   *
   * A manual override wins; otherwise memory_tool is asked, which honours the
   * pointer file, the legacy .memory/ folder and environment overrides alike.
   * Detection failure is not fatal -- the plugin falls back to the historical
   * default so its other commands keep working.
   */
  async resolveBaseFolder(): Promise<void> {
    const override = this.settings.baseFolder.trim();
    if (override) {
      this.baseName = override === "./" ? ROOT_BASE : override;
      return;
    }

    try {
      this.baseName = await this.cli.getBaseName();
    } catch (err: any) {
      this.baseName = DEFAULT_BASE;
      new Notice(
        `memory_tool: could not detect the knowledge base folder, using ` +
          `${DEFAULT_BASE}/. Set it manually in settings if that is wrong.`
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

    const current =
      this.plugin.baseName === ROOT_BASE ? "the vault root" : `${this.plugin.baseName}/`;

    new Setting(containerEl)
      .setName("Knowledge Base Folder")
      .setDesc(
        `Folder holding timeline/ and modules/, relative to the vault root. ` +
          `Leave empty to detect it automatically (currently: ${current}). ` +
          `Use "." for the vault root itself. Note that Obsidian hides ` +
          `dot-prefixed folders such as ".memory".`
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
