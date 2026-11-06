// Tests for the CLI layer. The last group runs the real memory_tool CLI on a
// synthetic knowledge base in a temporary folder.

import { test, describe, before, after } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

import { CliError, MemoryToolCli, findPython, parseResult } from "../src/cli.ts";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const python = process.env.MEMORY_TOOL_PYTHON || "python";

describe("findPython", () => {
  test("the setting comes first", () => {
    assert.equal(findPython(" C:/py/python.exe ", "/work", "win32", () => true), "C:/py/python.exe");
  });

  test("then the folder's .venv", () => {
    const seen = [];
    const found = findPython("", "/work", "win32", (file) => (seen.push(file), true));
    assert.equal(found, path.join("/work", ".venv", "Scripts", "python.exe"));
    assert.equal(findPython("", "/work", "linux", () => true), path.join("/work", ".venv", "bin", "python"));
  });

  test("then python on PATH", () => {
    assert.equal(findPython("", "/work", "win32", () => false), "python");
    assert.equal(findPython("", undefined), "python");
  });
});

describe("parseResult", () => {
  test("reads the last JSON line", () => {
    assert.deepEqual(parseResult('warning: something\n{"ok": true, "n": 1}\n'), { ok: true, n: 1 });
  });

  test("skips lines that only look like JSON", () => {
    assert.deepEqual(parseResult('{"ok": true}\n{not json\n'), { ok: true });
  });

  test("no JSON is bad_output", () => {
    assert.throws(() => parseResult("Traceback ...\n"), (e) => e instanceof CliError && e.code === "bad_output");
    assert.throws(() => parseResult("[1, 2]"), (e) => e.code === "bad_output");
  });
});

describe("running the CLI", () => {
  let root;
  let cli;

  before(() => {
    root = fs.mkdtempSync(path.join(os.tmpdir(), "mt-vscode-"));
    fs.writeFileSync(path.join(root, ".memory-tool.yml"), 'base: ".memory"\n');
    const base = path.join(root, ".memory");
    fs.mkdirSync(path.join(base, "timeline", "daily", "2026-03"), { recursive: true });
    fs.mkdirSync(path.join(base, "modules"), { recursive: true });
    fs.writeFileSync(path.join(base, "config.yaml"), "version: '1.0'\n");
    fs.writeFileSync(
      path.join(base, "timeline", "daily", "2026-03", "2026-03-01.md"),
      "# 2026-03-01 Timeline\n- 10:00 | [작업] 합성 기록 #시험\n손으로 적은 메모\n"
    );
    fs.writeFileSync(path.join(base, "modules", "server.md"), "# Server\n\n합성 문서입니다.\n");

    // Run this checkout's code, whatever is installed.
    process.env.PYTHONPATH = repo + path.delimiter + (process.env.PYTHONPATH ?? "");
    cli = new MemoryToolCli({ python, cwd: root, timeout: 60_000 });
  });

  after(() => fs.rmSync(root, { recursive: true, force: true }));

  test("finds the knowledge base", async () => {
    const info = await cli.base();
    assert.equal(info.found, true);
    assert.equal(fs.realpathSync(info.base), fs.realpathSync(path.join(root, ".memory")));
  });

  test("a folder whose .memory has no config.yaml is not a knowledge base", async () => {
    const other = fs.mkdtempSync(path.join(os.tmpdir(), "mt-vscode-none-"));
    try {
      fs.writeFileSync(path.join(other, ".memory-tool.yml"), 'base: ".memory"\n');
      fs.mkdirSync(path.join(other, ".memory", ".cache"), { recursive: true });
      const info = await new MemoryToolCli({ python, cwd: other }).base();
      assert.equal(info.found, false);
    } finally {
      fs.rmSync(other, { recursive: true, force: true });
    }
  });

  test("reads a period", async () => {
    const result = await cli.days("2026-03-01", "2026-03-02");
    assert.equal(result.days.length, 1);
    assert.deepEqual(result.days[0].entries, [
      { date: "2026-03-01", time: "10:00", text: "[작업] 합성 기록 #시험", tags: ["작업", "시험"] },
    ]);
    assert.match(result.days[0].content, /손으로 적은 메모/);
  });

  test("records any characters as written", async () => {
    const message = `따옴표 "큰" '작은' 100% $HOME %PATH% & | > ^ 이모지 ✓ 🙂`;
    const result = await cli.record(message);
    assert.equal(result.entry.text, message);

    const today = result.entry.date;
    const read = await cli.days(today, today);
    assert.ok(read.days[0].entries.some((entry) => entry.text === message));
  });

  test("a message that starts with a dash stays a message", async () => {
    const result = await cli.record("--json is not an option here");
    assert.equal(result.entry.text, "--json is not an option here");
  });

  test("keyword search", async () => {
    const result = await cli.search("합성", false);
    assert.equal(result.mode, "keyword");
    const kinds = result.results.map((hit) => hit.kind).sort();
    assert.ok(kinds.includes("timeline") && kinds.includes("module"));
    assert.equal(result.results.find((hit) => hit.kind === "timeline").entry.time, "10:00");
  });

  test("a failure carries the CLI's code", async () => {
    await assert.rejects(cli.days("2026-03-05", "2026-03-01"), (e) => e instanceof CliError && e.code === "invalid_argument");
  });

  test("a missing python is python_not_found", async () => {
    const missing = new MemoryToolCli({ python: path.join(root, "no-such-python.exe"), cwd: root });
    await assert.rejects(missing.days("2026-03-01", "2026-03-01"), (e) => e.code === "python_not_found");
  });

  test("a call that takes too long is timeout", async () => {
    await assert.rejects(cli.run(["days", "--json"], 1), (e) => e.code === "timeout");
  });
});
