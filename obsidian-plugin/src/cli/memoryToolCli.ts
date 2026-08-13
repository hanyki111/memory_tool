import { exec } from "child_process";

/** Resolved locations reported by `mbase show --json`. */
export interface BaseInfo {
  /** Absolute project root path */
  root: string;
  /** Absolute base folder path */
  base: string;
  /** Base folder name relative to the project root ("." = project root) */
  baseName: string;
  /** How the base was determined: pointer, legacy, env, nested-artifact, default */
  source: string;
  found: boolean;
}

export class MemoryToolCli {
  private pythonPath: string;
  private cwd: string;

  constructor(pythonPath: string = "python", cwd: string = "") {
    this.pythonPath = pythonPath || "python";
    this.cwd = cwd || "";
  }

  public setCwd(cwd: string) {
    this.cwd = cwd;
  }

  public setPythonPath(path: string) {
    this.pythonPath = path || "python";
  }

  private executeCommand(cmd: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const fullCmd = `${this.pythonPath} -m memory_tool ${cmd}`;
      const options = this.cwd ? { cwd: this.cwd } : {};

      exec(fullCmd, options, (error, stdout, stderr) => {
        if (error) {
          reject(new Error(stderr || error.message));
        } else {
          resolve(stdout.trim());
        }
      });
    });
  }

  /** Record a timeline entry (m "message") */
  public async recordTimeline(message: string): Promise<string> {
    const escapedMsg = message.replace(/"/g, '\\"');
    return this.executeCommand(`record "${escapedMsg}"`);
  }

  /** Create a new module (mmodule create name --desc desc --tags tags) */
  public async createModule(name: string, description: string = "", tags: string = ""): Promise<string> {
    let cmd = `module create "${name}"`;
    if (description) {
      cmd += ` --desc "${description.replace(/"/g, '\\"')}"`;
    }
    if (tags) {
      cmd += ` --tags "${tags.replace(/"/g, '\\"')}"`;
    }
    return this.executeCommand(cmd);
  }

  /** Get list of active modules */
  public async listModules(): Promise<string[]> {
    try {
      const output = await this.executeCommand("module list");
      const lines = output.split("\n");
      const modules: string[] = [];

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("- ")) {
          modules.push(trimmed.substring(2).trim());
        }
      }
      return modules;
    } catch {
      return [];
    }
  }

  /** Build AI Context (mcontext) */
  public async buildContext(): Promise<string> {
    return this.executeCommand("context");
  }

  /** Check module path health (mcheck) */
  public async checkHealth(): Promise<string> {
    return this.executeCommand("check");
  }

  /**
   * Ask memory_tool where the knowledge base is, as absolute paths.
   *
   * Absolute paths matter: the base *name* is relative to the project root,
   * while Obsidian needs a path relative to the vault root. Those differ
   * whenever the vault is the base folder itself.
   */
  public async getBaseInfo(): Promise<BaseInfo> {
    const output = await this.executeCommand("base show --json");

    // Other lines (update notices, warnings) may precede the JSON, so scan
    // backwards for the last line that parses as an object.
    const lines = output.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
    for (let i = lines.length - 1; i >= 0; i--) {
      if (!lines[i].startsWith("{")) continue;
      try {
        const data = JSON.parse(lines[i]);
        if (typeof data.base === "string" && typeof data.root === "string") {
          return {
            root: data.root,
            base: data.base,
            baseName: data.base_name ?? "",
            source: data.source ?? "unknown",
            found: Boolean(data.found),
          };
        }
      } catch {
        // keep scanning
      }
    }

    throw new Error("memory_tool did not report a usable base folder");
  }
}

