/**
 * Tests for the CLI command lines. The last test runs the real memory_tool CLI
 * on a synthetic knowledge base in a temporary folder.
 *
 * Run with: npm test
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

import { askArgs, commandParts, createModuleArgs, oneLine, recordArgs } from "../src/cli/args.ts";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

test("the Python setting: a plain name, a launcher with arguments, a quoted path", () => {
  assert.deepEqual(commandParts(""), ["python"]);
  assert.deepEqual(commandParts("python3"), ["python3"]);
  assert.deepEqual(commandParts("py -3"), ["py", "-3"]);
  assert.deepEqual(commandParts('"C:\\Program Files\\Python313\\python.exe"'), ["C:\\Program Files\\Python313\\python.exe"]);
  assert.deepEqual(commandParts('"C:\\My Py\\python.exe" -X utf8'), ["C:\\My Py\\python.exe", "-X", "utf8"]);
});

test("an existing path with spaces is used whole", () => {
  const exists = (p) => p === "C:\\Program Files\\Python313\\python.exe";
  assert.deepEqual(commandParts("C:\\Program Files\\Python313\\python.exe", exists), ["C:\\Program Files\\Python313\\python.exe"]);
});

test("text the person wrote comes after --", () => {
  assert.deepEqual(recordArgs("-dash first"), ["record", "--", "-dash first"]);
  assert.deepEqual(askArgs("q?", { simple: true, provider: "claude-cli" }), [
    "ask", "--json", "--simple", "--provider", "claude-cli", "--", "q?",
  ]);
  assert.deepEqual(createModuleArgs("work/api", "설명", "a,b", "참고"), [
    "module", "create", "--desc", "설명", "--tags", "a,b", "--type", "참고", "--", "work/api",
  ]);
  assert.deepEqual(createModuleArgs("x"), ["module", "create", "--", "x"]);
});

test("line breaks become spaces", () => {
  assert.equal(oneLine("a\r\nb\n\nc "), "a b c");
});

test("any characters reach the timeline as written", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mt-obsidian-"));
  try {
    fs.writeFileSync(path.join(root, ".memory-tool.yml"), 'base: ".memory"\n');
    fs.mkdirSync(path.join(root, ".memory", "timeline"), { recursive: true });
    fs.writeFileSync(path.join(root, ".memory", "config.yaml"), "version: '1.0'\n");

    const message = `따옴표 "큰" '작은' 100% $HOME %PATH% & | > ^ \\ 끝`;
    const [program, ...programArgs] = commandParts(process.env.MEMORY_TOOL_PYTHON || "python");
    execFileSync(program, [...programArgs, "-m", "memory_tool", ...recordArgs(message)], {
      cwd: root,
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: repo },
    });

    const files = fs.readdirSync(path.join(root, ".memory", "timeline"), { recursive: true })
      .filter((name) => String(name).endsWith(".md"));
    const text = fs.readFileSync(path.join(root, ".memory", "timeline", String(files[0])), "utf-8");
    // Python writes Windows line endings on Windows, so compare line by line.
    const lines = text.split(/\r?\n/);
    assert.ok(lines.some((line) => line.endsWith(` | ${message}`)), text);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
