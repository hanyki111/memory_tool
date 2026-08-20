/**
 * Tests for python-free timeline capture.
 *
 * Run with: node --test tests/
 *
 * These pin the plugin's output to memory_tool/core/timeline.py. Any drift here
 * splits a day's entries across two files or produces lines the CLI's reader
 * cannot parse, and neither failure is visible until someone searches for an
 * entry that quietly went missing.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_TIMELINE_CONFIG,
  appendEntry,
  candidatePaths,
  configuredFilenameLayout,
  filenameFor,
  formatEntry,
  headerFor,
  layoutFromFilenames,
  newFileBody,
  sanitizeMessage,
  sortMonthDirs,
  timelineConfigFrom,
  timelineDir,
  timelineMonthDirs,
  timelineRootDirs,
} from "../src/timeline/format.ts";

const AUG_17 = new Date(2026, 7, 17, 14, 30); // month is 0-based
const AUG_5 = new Date(2026, 7, 5, 9, 5);

// ---------------------------------------------------------------------------
// Filenames -- mirrors timeline_filename()
// ---------------------------------------------------------------------------

test("date layout uses the full ISO date", () => {
  assert.equal(filenameFor(AUG_17, "date"), "2026-08-17.md");
});

test("day layout uses a zero-padded day", () => {
  assert.equal(filenameFor(AUG_5, "day"), "05.md");
});

test("day layout pads to two digits", () => {
  // "5.md" would not match the _DAY_STEM the Python reader expects to pair with
  // its YYYY-MM folder, and the entry becomes unreachable.
  assert.equal(filenameFor(AUG_5, "day"), "05.md");
  assert.equal(filenameFor(AUG_17, "day"), "17.md");
});

// ---------------------------------------------------------------------------
// Candidate paths -- mirrors Timeline.candidate_paths
// ---------------------------------------------------------------------------

test("all four layouts are considered, most current first", () => {
  assert.deepEqual(candidatePaths(".memory", AUG_17), [
    ".memory/timeline/daily/2026-08/2026-08-17.md",
    ".memory/timeline/daily/2026-08/17.md",
    ".memory/timeline/2026-08/2026-08-17.md",
    ".memory/timeline/2026-08/17.md",
  ]);
});

test("an empty prefix means the vault root is the base folder", () => {
  // The common setup: the .memory folder itself is opened as the vault.
  assert.deepEqual(candidatePaths("", AUG_17), [
    "timeline/daily/2026-08/2026-08-17.md",
    "timeline/daily/2026-08/17.md",
    "timeline/2026-08/2026-08-17.md",
    "timeline/2026-08/17.md",
  ]);
});

test("new files go under daily/", () => {
  assert.equal(timelineDir(".memory", AUG_17), ".memory/timeline/daily/2026-08");
});

// ---------------------------------------------------------------------------
// Entry formatting -- mirrors Timeline.format_entry
// ---------------------------------------------------------------------------

test("plain entry", () => {
  assert.equal(formatEntry(AUG_17, "Hello"), "- 14:30 | Hello");
});

test("time is zero-padded", () => {
  assert.equal(formatEntry(AUG_5, "Morning"), "- 09:05 | Morning");
});

test("bracket tags are prepended", () => {
  assert.equal(
    formatEntry(AUG_17, "Hello", ["work", "deep focus"], "bracket"),
    "- 14:30 | [work] [deep-focus] Hello"
  );
});

test("hashtag tags are appended", () => {
  assert.equal(
    formatEntry(AUG_17, "Hello", ["work", "deep focus"], "hashtag"),
    "- 14:30 | Hello #work #deep-focus"
  );
});

test("blank tags are dropped, not rendered empty", () => {
  assert.equal(formatEntry(AUG_17, "Hello", ["  ", ""], "bracket"), "- 14:30 | Hello");
});

// ---------------------------------------------------------------------------
// File bodies -- mirrors write_timeline
// ---------------------------------------------------------------------------

test("header carries the full date regardless of filename layout", () => {
  assert.equal(headerFor(AUG_17), "# 2026-08-17 Timeline");
});

test("a new file gets a header and one trailing newline", () => {
  assert.equal(
    newFileBody(AUG_17, "- 14:30 | Hi"),
    "# 2026-08-17 Timeline\n- 14:30 | Hi\n"
  );
});

test("appending keeps exactly one trailing newline", () => {
  assert.equal(
    appendEntry("# 2026-08-17 Timeline\n- 09:00 | First\n", "- 14:30 | Second"),
    "# 2026-08-17 Timeline\n- 09:00 | First\n- 14:30 | Second\n"
  );
});

test("appending normalizes a file that ended with several newlines", () => {
  assert.equal(
    appendEntry("# 2026-08-17 Timeline\n- 09:00 | First\n\n\n", "- 14:30 | Second"),
    "# 2026-08-17 Timeline\n- 09:00 | First\n- 14:30 | Second\n"
  );
});

test("appending to a file with no trailing newline still separates entries", () => {
  assert.equal(
    appendEntry("# 2026-08-17 Timeline\n- 09:00 | First", "- 14:30 | Second"),
    "# 2026-08-17 Timeline\n- 09:00 | First\n- 14:30 | Second\n"
  );
});

// ---------------------------------------------------------------------------
// Message sanitizing
// ---------------------------------------------------------------------------

test("newlines collapse so one entry stays one line", () => {
  // A raw newline would be read back as a separate, malformed entry.
  assert.equal(sanitizeMessage("first\nsecond\r\nthird"), "first second third");
});

test("surrounding whitespace is trimmed", () => {
  assert.equal(sanitizeMessage("  padded  "), "padded");
});

// ---------------------------------------------------------------------------
// Config reading
// ---------------------------------------------------------------------------

test("config picks up the date layout", () => {
  const config = timelineConfigFrom({ timeline: { filename: "date" } });
  assert.equal(config.filenameLayout, "date");
});

test("missing config falls back to the Python defaults", () => {
  assert.deepEqual(timelineConfigFrom({}), DEFAULT_TIMELINE_CONFIG);
  assert.deepEqual(timelineConfigFrom(null), DEFAULT_TIMELINE_CONFIG);
});

test("an unknown layout value falls back rather than being trusted", () => {
  assert.equal(timelineConfigFrom({ timeline: { filename: "weekly" } }).filenameLayout, "day");
});

test("tag storage format is read from config", () => {
  assert.equal(timelineConfigFrom({ tag: { storage_format: "hashtag" } }).tagFormat, "hashtag");
});

// ---------------------------------------------------------------------------
// Layout inferred from filenames -- the fallback for an unreadable config.yaml
// ---------------------------------------------------------------------------

test("a folder of ISO-dated files means the date layout", () => {
  assert.equal(
    layoutFromFilenames(["2026-08-17.md", "2026-08-18.md", "2026-08-19.md"]),
    "date"
  );
});

test("a folder of day-numbered files means the day layout", () => {
  assert.equal(layoutFromFilenames(["05.md", "17.md", "9.md"]), "day");
});

test("non-timeline files in the folder are ignored", () => {
  // A month folder can hold a summary or an index; neither says anything about
  // how the timeline files themselves are named.
  assert.equal(layoutFromFilenames(["README.md", "summary.md", "2026-08-17.md"]), "date");
  assert.equal(layoutFromFilenames(["README.md", "notes.md"]), null);
});

test("an empty folder yields no answer rather than a guess", () => {
  assert.equal(layoutFromFilenames([]), null);
});

test("the majority wins in a part-migrated folder", () => {
  assert.equal(layoutFromFilenames(["2026-08-17.md", "2026-08-18.md", "19.md"]), "date");
  assert.equal(layoutFromFilenames(["17.md", "18.md", "2026-08-19.md"]), "day");
});

test("a tie resolves to date", () => {
  // Only a half-finished migration produces a tie, and migrations run toward
  // "date" -- that is the layout the Calendar plugin needs.
  assert.equal(layoutFromFilenames(["17.md", "2026-08-18.md"]), "date");
});

// ---------------------------------------------------------------------------
// Folders scanned to infer the layout
// ---------------------------------------------------------------------------

test("both month folder layouts are scanned, most current first", () => {
  assert.deepEqual(timelineMonthDirs(".memory", AUG_17), [
    ".memory/timeline/daily/2026-08",
    ".memory/timeline/2026-08",
  ]);
});

test("month folders are searched from both timeline roots", () => {
  assert.deepEqual(timelineRootDirs(".memory"), [
    ".memory/timeline/daily",
    ".memory/timeline",
  ]);
});

test("only YYYY-MM folders count, newest first", () => {
  assert.deepEqual(sortMonthDirs(["2026-07", "archive", "2026-08", "2025-12", ".trash"]), [
    "2026-08",
    "2026-07",
    "2025-12",
  ]);
});

// ---------------------------------------------------------------------------
// "config says nothing" vs "config says day"
// ---------------------------------------------------------------------------

test("a silent config reports no layout, so the files on disk can decide", () => {
  // The distinction is the whole point: returning "day" here would look like a
  // deliberate choice and would out-rank a knowledge base full of dated files.
  assert.equal(configuredFilenameLayout({}), null);
  assert.equal(configuredFilenameLayout(null), null);
  assert.equal(configuredFilenameLayout({ timeline: {} }), null);
  assert.equal(configuredFilenameLayout({ timeline: { filename: "weekly" } }), null);
});

test("a stated layout is reported as stated", () => {
  assert.equal(configuredFilenameLayout({ timeline: { filename: "date" } }), "date");
  assert.equal(configuredFilenameLayout({ timeline: { filename: "day" } }), "day");
});
