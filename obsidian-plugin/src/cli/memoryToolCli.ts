import { exec } from "child_process";

/**
 * Escape a value for embedding in a double-quoted shell argument.
 *
 * Backslashes first, then quotes -- reversing the order would double-escape the
 * backslashes introduced by the quote replacement. Newlines are collapsed
 * because a raw newline would terminate the command.
 */
function escapeArg(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/[\r\n]+/g, " ")
    .trim();
}

/**
 * Find the last line of output that parses as a JSON object.
 *
 * Update notices and warnings can precede the payload, so scanning backwards is
 * more robust than assuming the JSON is the only output.
 */
function parseLastJsonObject(output: string): Record<string, any> | null {
  const lines = output
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("{"));

  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const data = JSON.parse(lines[i]);
      if (data && typeof data === "object") return data;
    } catch {
      // keep scanning
    }
  }
  return null;
}

/** Per-call overrides for a CLI invocation. */
interface ExecOptions {
  /** Kill the process after this many ms (LLM calls need a generous value). */
  timeout?: number;
  /** stdout buffer cap; long answers and module lists can be large. */
  maxBuffer?: number;
}

/** A memory Q&A result from `mask --json`. */
export interface AskResult {
  question: string;
  answer: string;
  provider: string;
  /** "agent" (tool-using) or "simple" (keyword RAG) */
  mode: string;
  /** Tools the agent invoked; empty in simple mode */
  tools: string[];
  /** Files that supplied context, vault-relative where available */
  sources: string[];
}

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

  private executeCommand(cmd: string, opts: ExecOptions = {}): Promise<string> {
    return new Promise((resolve, reject) => {
      const fullCmd = `${this.pythonPath} -m memory_tool ${cmd}`;

      const options: Record<string, unknown> = {
        // memory_tool prints Korean; without this Windows uses cp949 and mangles it.
        env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        maxBuffer: opts.maxBuffer ?? 1024 * 1024 * 16,
      };
      if (this.cwd) options.cwd = this.cwd;
      if (opts.timeout) options.timeout = opts.timeout;

      exec(fullCmd, options, (error, stdout, stderr) => {
        if (error) {
          // A failing command may still have written a useful message to stdout
          // (the CLI reports errors there), so prefer whichever is non-empty.
          const detail = (stderr || "").trim() || (stdout || "").trim();
          reject(new Error(detail || error.message));
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
   * Ask a natural-language question about the knowledge base (mask).
   *
   * Uses --json so the answer arrives unwrapped: the human-facing output is
   * hard-wrapped to the terminal width, which inserts line breaks mid-sentence
   * and breaks Markdown rendering in a note.
   *
   * @param question Natural language question
   * @param opts simple: keyword RAG instead of the agent; provider: override;
   *             timeoutMs: how long to wait for the model
   */
  public async ask(
    question: string,
    opts: { simple?: boolean; provider?: string; timeoutMs?: number } = {}
  ): Promise<AskResult> {
    const parts = [`ask "${escapeArg(question)}"`, "--json"];
    if (opts.simple) parts.push("--simple");
    if (opts.provider) parts.push(`--provider "${escapeArg(opts.provider)}"`);

    const output = await this.executeCommand(parts.join(" "), {
      timeout: opts.timeoutMs ?? 300000,
    });

    const data = parseLastJsonObject(output);
    if (!data) {
      throw new Error(`Could not parse the answer from memory_tool:\n${output}`);
    }
    if (data.ok === false) {
      const providers = Array.isArray(data.available_providers)
        ? data.available_providers.join(", ")
        : "";
      throw new Error(
        String(data.error ?? "memory_tool reported a failure") +
          (providers ? ` (available providers: ${providers})` : "")
      );
    }

    return {
      question: String(data.question ?? question),
      answer: String(data.answer ?? ""),
      provider: String(data.provider ?? "unknown"),
      mode: String(data.mode ?? ""),
      tools: Array.isArray(data.tools) ? data.tools.map(String) : [],
      sources: Array.isArray(data.sources) ? data.sources.map(String) : [],
    };
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
    const data = parseLastJsonObject(output);

    if (!data || typeof data.base !== "string" || typeof data.root !== "string") {
      throw new Error("memory_tool did not report a usable base folder");
    }

    return {
      root: data.root,
      base: data.base,
      baseName: data.base_name ?? "",
      source: data.source ?? "unknown",
      found: Boolean(data.found),
    };
  }
}

