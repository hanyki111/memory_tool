/**
 * Calls the memory_tool CLI with --json and reads its one-line result.
 *
 * No VS Code API here, so the module runs under `node --test`.
 *
 * Arguments go to execFile as an array, never through a shell, so a message
 * with quotes, %, $ or any other character reaches the CLI as written.
 */

import { execFile } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";

export interface Entry {
  date: string;
  time: string;
  /** The line as written, tags included */
  text: string;
  tags: string[];
}

export interface Day {
  date: string;
  path: string;
  entries: Entry[];
  /** The whole file, which keeps lines that are not entries */
  content: string;
}

export interface Notice {
  kind: string;
  message: string;
}

export interface DaysResult {
  from: string;
  to: string;
  days: Day[];
}

export interface RecordResult {
  entry: Entry;
  path: string;
  notices: Notice[];
}

export interface SearchHit {
  path: string;
  kind: string;
  line: number;
  text: string;
  context: string;
  score: number;
  date: string | null;
  entry?: Entry;
}

export interface SearchResult {
  query: string;
  mode: string;
  cached: boolean;
  results: SearchHit[];
  notices: Notice[];
}

export interface BaseInfo {
  root: string;
  base: string;
  found: boolean;
}

/** Codes this module adds to those the CLI reports. */
export const PYTHON_NOT_FOUND = "python_not_found";
export const TIMEOUT = "timeout";
export const BAD_OUTPUT = "bad_output";

export class CliError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

/**
 * Choose the Python to run memory_tool with.
 *
 * The setting first, then the folder's virtual environment, then `python` on PATH.
 */
export function findPython(
  configured: string,
  folder: string | undefined,
  platform: string = process.platform,
  exists: (file: string) => boolean = fs.existsSync
): string {
  if (configured.trim()) {
    return configured.trim();
  }

  if (folder) {
    const candidate =
      platform === "win32"
        ? path.join(folder, ".venv", "Scripts", "python.exe")
        : path.join(folder, ".venv", "bin", "python");
    if (exists(candidate)) {
      return candidate;
    }
  }

  return "python";
}

/**
 * Read the result: the last line of output that parses as a JSON object.
 *
 * The CLI prints only that line in JSON mode; looking for the last one keeps a
 * stray warning from a library from breaking the result.
 */
export function parseResult(stdout: string): Record<string, unknown> {
  const lines = stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

  for (let i = lines.length - 1; i >= 0; i--) {
    if (!lines[i].startsWith("{")) {
      continue;
    }
    try {
      const value = JSON.parse(lines[i]);
      if (value && typeof value === "object" && !Array.isArray(value)) {
        return value as Record<string, unknown>;
      }
    } catch {
      // Not JSON after all; keep looking.
    }
  }

  throw new CliError(BAD_OUTPUT, `memory_tool printed no JSON result: ${tail(stdout)}`);
}

function tail(text: string, length = 300): string {
  const trimmed = text.trim();
  return trimmed.length > length ? `…${trimmed.slice(-length)}` : trimmed || "(nothing)";
}

export interface CliOptions {
  python: string;
  /** The folder the CLI runs in, which decides the knowledge base */
  cwd: string;
  /** Milliseconds before a call is given up */
  timeout?: number;
}

export class MemoryToolCli {
  readonly python: string;
  readonly cwd: string;
  readonly timeout: number;

  constructor(options: CliOptions) {
    this.python = options.python;
    this.cwd = options.cwd;
    this.timeout = options.timeout ?? 60_000;
  }

  /** Run `python -m memory_tool <args>` and return its result, or throw a CliError. */
  run(args: string[], timeout: number = this.timeout): Promise<Record<string, unknown>> {
    return new Promise((resolve, reject) => {
      execFile(
        this.python,
        ["-m", "memory_tool", ...args],
        {
          cwd: this.cwd,
          env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" },
          timeout,
          maxBuffer: 64 * 1024 * 1024,
          windowsHide: true,
          encoding: "utf8",
        },
        (error, stdout, stderr) => {
          if (error && (error as NodeJS.ErrnoException).code === "ENOENT") {
            reject(new CliError(PYTHON_NOT_FOUND, `Python not found: ${this.python}`));
            return;
          }
          if (error && error.killed) {
            reject(new CliError(TIMEOUT, `memory_tool did not answer within ${Math.round(timeout / 1000)} s`));
            return;
          }

          let result: Record<string, unknown>;
          try {
            result = parseResult(stdout);
          } catch (parseError) {
            const detail = tail(stderr || stdout);
            reject(error ? new CliError(BAD_OUTPUT, `memory_tool failed: ${detail}`) : parseError);
            return;
          }

          if (result.ok === false) {
            reject(new CliError(String(result.code ?? "failed"), String(result.error ?? "memory_tool failed")));
            return;
          }
          resolve(result);
        }
      );
    });
  }

  /**
   * Where the knowledge base is.
   *
   * A base counts only if it holds config.yaml, which `minit` writes. The CLI
   * searches upward and would otherwise take ~/.memory, the global cache
   * folder, for a knowledge base.
   */
  async base(): Promise<BaseInfo> {
    const result = await this.run(["base", "show", "--json"]);
    const base = String(result.base ?? "");
    const found = Boolean(result.found) && base !== "" && fs.existsSync(path.join(base, "config.yaml"));
    return { root: String(result.root ?? ""), base, found };
  }

  /** The timeline from one date to another, both YYYY-MM-DD and included. */
  async days(from: string, to: string): Promise<DaysResult> {
    return (await this.run(["days", "--from", from, "--to", to, "--json"])) as unknown as DaysResult;
  }

  /** Record a message. Tags are written in it, as [tag] or #tag. */
  async record(message: string): Promise<RecordResult> {
    // "--" ends the options, so a message starting with "-" stays a message.
    return (await this.run(["record", "--json", "--", message])) as unknown as RecordResult;
  }

  /** Keyword search, or hybrid search when `semantic` is set. */
  async search(query: string, semantic: boolean): Promise<SearchResult> {
    const mode = semantic ? "--hybrid" : "--no-hybrid";
    // Hybrid search loads the embedding model on every call, so it gets longer.
    const timeout = semantic ? Math.max(this.timeout, 120_000) : this.timeout;
    // --no-cache: the CLI keeps results for an hour, which would hide entries
    // recorded since.
    return (await this.run(["search", mode, "--no-cache", "--json", "--", query], timeout)) as unknown as SearchResult;
  }

  /** The command line that starts a review from a date, for a terminal. */
  reviewCommand(since: string): string[] {
    return [this.python, "-m", "memory_tool", "review", "--since", since];
  }
}
