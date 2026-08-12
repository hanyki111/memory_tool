import { exec } from "child_process";

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
}
