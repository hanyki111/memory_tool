/**
 * Tests for the filesystem-only replacements for `mbase show` and `mmodule list`.
 *
 * Run with: node --test tests/
 *
 * These matter most on mobile, where there is no Python and these are the only
 * implementations available. Getting the base folder wrong there writes capture
 * into a directory no command will ever read.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  BASE_CANDIDATES,
  listModules,
  probeBasePrefix,
} from "../src/vaultScan.ts";

/**
 * In-memory adapter over a flat list of file paths.
 * Folders are inferred, so tests only declare the files that exist.
 */
function fakeAdapter(files) {
  const fileSet = new Set(files);

  const folders = new Set();
  for (const file of files) {
    const parts = file.split("/");
    for (let i = 1; i < parts.length; i++) {
      folders.add(parts.slice(0, i).join("/"));
    }
  }

  return {
    async exists(path) {
      const p = path.replace(/\/+$/, "");
      if (p === "") return true;
      return fileSet.has(p) || folders.has(p);
    },
    async list(path) {
      const prefix = path === "" ? "" : `${path.replace(/\/+$/, "")}/`;
      const childFiles = [];
      const childFolders = new Set();

      for (const file of fileSet) {
        if (!file.startsWith(prefix)) continue;
        const rest = file.slice(prefix.length);
        if (!rest) continue;
        const slash = rest.indexOf("/");
        if (slash === -1) childFiles.push(file);
        else childFolders.add(prefix + rest.slice(0, slash));
      }

      return { files: childFiles.sort(), folders: [...childFolders].sort() };
    },
  };
}

// ---------------------------------------------------------------------------
// Base folder probing
// ---------------------------------------------------------------------------

test("finds a base at the vault root", () => {
  // The common setup: the .memory folder itself was opened as the vault.
  const adapter = fakeAdapter(["timeline/daily/2026-08/17.md", "modules/a/a.md"]);
  return probeBasePrefix(adapter).then((prefix) => assert.equal(prefix, ""));
});

test("finds a base in .memory/", async () => {
  const adapter = fakeAdapter([
    ".memory/timeline/daily/2026-08/17.md",
    ".memory/modules/a/a.md",
  ]);
  assert.equal(await probeBasePrefix(adapter), ".memory");
});

test("finds a base in a renamed folder", async () => {
  const adapter = fakeAdapter(["memory/timeline/x.md", "memory/modules/a/a.md"]);
  assert.equal(await probeBasePrefix(adapter), "memory");
});

test("both marker folders are required", async () => {
  // timeline/ alone is not a knowledge base; guessing here would send capture
  // into a folder no command reads.
  const adapter = fakeAdapter([".memory/timeline/x.md"]);
  assert.equal(await probeBasePrefix(adapter), null);
});

test("returns null rather than guessing when nothing matches", async () => {
  assert.equal(await probeBasePrefix(fakeAdapter(["notes/hello.md"])), null);
});

test("the vault root is checked first", async () => {
  // Both would match; the root is the more specific answer for this vault.
  const adapter = fakeAdapter([
    "timeline/x.md",
    "modules/a/a.md",
    ".memory/timeline/y.md",
    ".memory/modules/b/b.md",
  ]);
  assert.equal(await probeBasePrefix(adapter), "");
  assert.equal(BASE_CANDIDATES[0], "");
});

// ---------------------------------------------------------------------------
// Module discovery -- mirrors ModuleManager.discover_all_modules
// ---------------------------------------------------------------------------

test("folder-encapsulated modules (A/B/B.md)", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/memory-tool/core-system/core-system.md",
    ".memory/modules/memory-tool/memory-tool.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), [
    "memory-tool",
    "memory-tool/core-system",
  ]);
});

test("flat single-file modules (A/B.md)", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/AI/asyncio.md",
    ".memory/modules/AI/vectors.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), [
    "AI/asyncio",
    "AI/vectors",
  ]);
});

test("legacy multi-file modules are named by their folder", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/legacy/thing/module.md",
    ".memory/modules/legacy/thing/current.md",
    ".memory/modules/legacy/thing/decisions.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), ["legacy/thing"]);
});

test("archive folders are skipped", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/a/a.md",
    ".memory/modules/a/archive/old.md",
    ".memory/modules/archive/gone/gone.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), ["a"]);
});

test("underscore and all-caps files are not modules", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/a/a.md",
    ".memory/modules/_index.md",
    ".memory/modules/a/PLAN.md",
    ".memory/modules/MIGRATION-SUMMARY.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), ["a"]);
});

test("non-markdown files are ignored", async () => {
  const adapter = fakeAdapter([".memory/modules/a/a.md", ".memory/modules/a/notes.txt"]);
  assert.deepEqual(await listModules(adapter, ".memory"), ["a"]);
});

test("Korean module paths survive intact", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/게임 분석/니케/니케.md",
    ".memory/modules/게임 분석/게임 분석.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), [
    "게임 분석",
    "게임 분석/니케",
  ]);
});

test("an empty prefix means the vault root is the base", async () => {
  const adapter = fakeAdapter(["modules/a/a.md"]);
  assert.deepEqual(await listModules(adapter, ""), ["a"]);
});

test("a missing modules folder yields an empty list, not an error", async () => {
  assert.deepEqual(await listModules(fakeAdapter([]), ".memory"), []);
});

test("hidden folders inside modules/ are skipped", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/a/a.md",
    ".memory/modules/.obsidian/workspace.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), ["a"]);
});

test("a module and its child are both listed", async () => {
  const adapter = fakeAdapter([
    ".memory/modules/parent/parent.md",
    ".memory/modules/parent/child/child.md",
  ]);

  assert.deepEqual(await listModules(adapter, ".memory"), ["parent", "parent/child"]);
});
