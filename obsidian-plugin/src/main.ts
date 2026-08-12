import { Plugin, Notice, PluginSettingTab, Setting, App } from "obsidian";
import { MemoryToolCli } from "./cli/memoryToolCli";
import { RecordModal } from "./modals/RecordModal";
import { CreateModuleModal } from "./modals/CreateModuleModal";
import { ModuleSuggestModal } from "./modals/ModuleSuggestModal";

interface MemoryToolSettings {
  pythonPath: string;
}

const DEFAULT_SETTINGS: MemoryToolSettings = {
  pythonPath: "python",
};

export default class MemoryToolPlugin extends Plugin {
  settings: MemoryToolSettings = DEFAULT_SETTINGS;
  cli: MemoryToolCli = new MemoryToolCli();

  async onload() {
    await this.loadSettings();

    // Get current vault root path
    // @ts-ignore
    const basePath = this.app.vault.adapter.getBasePath ? this.app.vault.adapter.getBasePath() : "";
    this.cli.setCwd(basePath);
    this.cli.setPythonPath(this.settings.pythonPath);

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
        new CreateModuleModal(this.app, this.cli).open();
      },
    });

    // 5. Command: Go to Module (Hotkey: Ctrl+Alt+G)
    this.addCommand({
      id: "go-to-module",
      name: "Go to Module",
      hotkeys: [{ modifiers: ["Mod", "Alt"], key: "g" }],
      callback: () => {
        new ModuleSuggestModal(this.app, this.cli).open();
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

    // Settings Tab
    this.addSettingTab(new MemoryToolSettingTab(this.app, this));
  }

  onunload() {}

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
    this.cli.setPythonPath(this.settings.pythonPath);
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
  }
}
