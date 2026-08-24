/**
 * Tests for vault-relative path construction.
 *
 * Run with: node --test tests/
 *
 * These cover the two bugs that made the plugin unusable when the vault was the
 * .memory folder itself:
 *   1. Using the base *name* as the vault prefix produced .memory/.memory/...
 *   2. `mmodule list` prints nested names with the host separator, so Windows
 *      backslashes leaked into vault paths.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_BASE,
  describePrefix,
  moduleCandidatePaths,
  moduleNameFromPath,
  modulePrefixFromFolder,
  normalizePrefix,
  underBase,
  vaultRelativeBase,
} from "../src/paths.ts";

const SEP = String.fromCharCode(92); // a single backslash

// ---------------------------------------------------------------------------
// vaultRelativeBase -- the core fix
// ---------------------------------------------------------------------------

test("vault is the project root, base is a subfolder", () => {
  assert.equal(
    vaultRelativeBase("E:\\proj", "E:\\proj\\.memory"),
    ".memory"
  );
});

test("vault IS the base folder -> empty prefix", () => {
  // The reported bug: returning ".memory" here yields .memory/.memory/...
  assert.equal(
    vaultRelativeBase("E:\\proj\\.memory", "E:\\proj\\.memory"),
    ""
  );
});

test("visible base folder name", () => {
  assert.equal(vaultRelativeBase("E:\\proj", "E:\\proj\\memory"), "memory");
});

test("nested base folder path", () => {
  assert.equal(
    vaultRelativeBase("E:\\proj", "E:\\proj\\a\\b"),
    "a/b"
  );
});

test("drive-letter case mismatch still matches", () => {
  // Obsidian and Python can disagree on drive-letter case.
  assert.equal(
    vaultRelativeBase("E:\\proj\\.memory", "e:\\proj\\.memory"),
    ""
  );
});

test("mixed separators are tolerated", () => {
  assert.equal(vaultRelativeBase("E:/proj", "E:\\proj\\memory"), "memory");
});

test("trailing separators are tolerated", () => {
  assert.equal(vaultRelativeBase("E:\\proj\\", "E:\\proj\\memory"), "memory");
});

test("base outside the vault returns null", () => {
  assert.equal(vaultRelativeBase("E:\\proj\\vault", "E:\\other\\.memory"), null);
});

test("vault inside the base returns null", () => {
  // Obsidian cannot address a parent directory with a relative path.
  assert.equal(vaultRelativeBase("E:\\proj\\.memory\\sub", "E:\\proj\\.memory"), null);
});

test("a sibling with a shared name prefix is not treated as inside", () => {
  assert.equal(vaultRelativeBase("E:\\proj\\vault", "E:\\proj\\vault-other"), null);
});

test("empty inputs return null", () => {
  assert.equal(vaultRelativeBase("", "E:\\proj\\.memory"), null);
  assert.equal(vaultRelativeBase("E:\\proj", ""), null);
});

// ---------------------------------------------------------------------------
// normalizePrefix -- manual override handling
// ---------------------------------------------------------------------------

test("dot spellings mean the vault root", () => {
  for (const raw of [".", "./", " . ", ""]) {
    assert.equal(normalizePrefix(raw), "");
  }
});

test("plain names pass through, trimmed", () => {
  assert.equal(normalizePrefix("  memory  "), "memory");
  assert.equal(normalizePrefix("memory/"), "memory");
  assert.equal(normalizePrefix("./memory"), "memory");
  assert.equal(normalizePrefix(".memory"), ".memory");
});

test("backslashes in an override are normalized", () => {
  assert.equal(normalizePrefix("a" + SEP + "b"), "a/b");
});

// ---------------------------------------------------------------------------
// moduleCandidatePaths -- both module layouts, both separators
// ---------------------------------------------------------------------------

test("flat module name, empty prefix", () => {
  assert.deepEqual(moduleCandidatePaths("", "master"), [
    "modules/master/master.md",
    "modules/master.md",
  ]);
});

test("flat module name, with prefix", () => {
  assert.deepEqual(moduleCandidatePaths(".memory", "master"), [
    ".memory/modules/master/master.md",
    ".memory/modules/master.md",
  ]);
});

test("nested name with backslashes becomes forward-slashed", () => {
  // What `mmodule list` prints on Windows.
  assert.deepEqual(moduleCandidatePaths("", "AI" + SEP + "AI 기초"), [
    "modules/AI/AI 기초/AI 기초.md",
    "modules/AI/AI 기초.md",
  ]);
});

test("deeply nested name with backslashes", () => {
  const name = ["AI", "AI 기초", "nlp-vectorization"].join(SEP);
  assert.deepEqual(moduleCandidatePaths("", name), [
    "modules/AI/AI 기초/nlp-vectorization/nlp-vectorization.md",
    "modules/AI/AI 기초/nlp-vectorization.md",
  ]);
});

test("no vault path ever contains a backslash", () => {
  for (const p of moduleCandidatePaths(".memory", "a" + SEP + "b" + SEP + "c")) {
    assert.ok(!p.includes(SEP), `backslash leaked into ${p}`);
  }
});

test("repeated and stray separators are collapsed", () => {
  assert.deepEqual(moduleCandidatePaths("", "/AI//sub/"), [
    "modules/AI/sub/sub.md",
    "modules/AI/sub.md",
  ]);
});

test("both module layouts are offered, encapsulated first", () => {
  const [first, second] = moduleCandidatePaths("", "A/B");
  assert.equal(first, "modules/A/B/B.md"); // [Folder]/[Folder].md
  assert.equal(second, "modules/A/B.md"); // .md beside its subfolder
});

// ---------------------------------------------------------------------------
// underBase / describePrefix
// ---------------------------------------------------------------------------

test("underBase omits an empty prefix", () => {
  assert.equal(underBase("", "timeline", "daily"), "timeline/daily");
});

test("underBase applies a prefix", () => {
  assert.equal(underBase("memory", "timeline", "daily"), "memory/timeline/daily");
});

test("underBase never emits a leading slash", () => {
  assert.ok(!underBase("", "timeline").startsWith("/"));
});

test("describePrefix is human readable", () => {
  assert.equal(describePrefix(""), "the vault root");
  assert.equal(describePrefix("memory"), "memory/");
});

test("DEFAULT_BASE is the historical default", () => {
  assert.equal(DEFAULT_BASE, ".memory");
});

// ---------------------------------------------------------------------------
// moduleNameFromPath -- the inverse of moduleCandidatePaths
// ---------------------------------------------------------------------------

test("encapsulated layout drops the repeated leaf", () => {
  assert.equal(
    moduleNameFromPath(".memory", ".memory/modules/A/B/B.md"),
    "A/B"
  );
});

test("flat layout keeps every segment", () => {
  assert.equal(moduleNameFromPath(".memory", ".memory/modules/A/B.md"), "A/B");
});

test("top-level encapsulated module names itself", () => {
  assert.equal(moduleNameFromPath(".memory", ".memory/modules/A/A.md"), "A");
});

test("a vault rooted at the base folder needs no prefix", () => {
  assert.equal(moduleNameFromPath("", "modules/A/A.md"), "A");
});

test("a file outside modules is not a module", () => {
  assert.equal(moduleNameFromPath(".memory", ".memory/timeline/daily.md"), null);
  assert.equal(moduleNameFromPath(".memory", "notes/scratch.md"), null);
});

test("archived modules are not offered", () => {
  assert.equal(
    moduleNameFromPath(".memory", ".memory/modules/archive/A/A.md"),
    null
  );
});

test("a non-markdown file is not a module", () => {
  assert.equal(moduleNameFromPath(".memory", ".memory/modules/A/img.png"), null);
});

test("backslashes from the host separator are accepted", () => {
  assert.equal(
    moduleNameFromPath(".memory", `.memory${SEP}modules${SEP}A${SEP}A.md`),
    "A"
  );
});

// ---------------------------------------------------------------------------
// modulePrefixFromFolder -- pre-filling the create dialog
// ---------------------------------------------------------------------------

test("the modules folder itself prefills nothing", () => {
  assert.equal(modulePrefixFromFolder(".memory", ".memory/modules"), "");
});

test("a nested folder prefills its own path", () => {
  assert.equal(modulePrefixFromFolder(".memory", ".memory/modules/A/B"), "A/B");
});

test("a folder outside modules gets no menu entry", () => {
  assert.equal(modulePrefixFromFolder(".memory", ".memory/timeline"), null);
  assert.equal(modulePrefixFromFolder(".memory", "attachments"), null);
});

test("the archive gets no menu entry", () => {
  assert.equal(modulePrefixFromFolder(".memory", ".memory/modules/archive"), null);
  assert.equal(
    modulePrefixFromFolder(".memory", ".memory/modules/archive/old"),
    null
  );
});

test("a folder merely starting with the same letters is not inside", () => {
  assert.equal(modulePrefixFromFolder(".memory", ".memory/modules-old/A"), null);
});
