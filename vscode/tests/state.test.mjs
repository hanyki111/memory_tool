import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  addDays,
  clearSearch,
  initial,
  isDate,
  jump,
  jumpEndingAt,
  localToday,
  olderPage,
  receive,
  refreshRange,
  reviewSince,
  withSearch,
} from "../src/state.ts";

const day = (date, ...texts) => ({
  date,
  path: `/kb/${date}.md`,
  entries: texts.map((text, i) => ({ date, time: `1${i}:00`, text, tags: [] })),
  content: texts.join("\n"),
});

describe("dates", () => {
  test("adds days across months and years", () => {
    assert.equal(addDays("2026-03-01", -1), "2026-02-28");
    assert.equal(addDays("2024-02-28", 1), "2024-02-29");
    assert.equal(addDays("2026-12-31", 1), "2027-01-01");
  });

  test("checks dates", () => {
    assert.ok(isDate("2026-02-28"));
    assert.ok(!isDate("2026-02-30"));
    assert.ok(!isDate("26-02-01"));
  });

  test("today is local", () => {
    assert.equal(localToday(new Date(2026, 0, 5, 23, 59)), "2026-01-05");
  });
});

describe("scrolling", () => {
  test("opens on the last seven days", () => {
    assert.deepEqual(initial("2026-11-06").loaded, { from: "2026-10-31", to: "2026-11-06" });
  });

  test("each page goes back seven days without asking again for loaded ones", () => {
    let state = initial("2026-11-06");
    state = receive(state, state.loaded, [day("2026-11-06", "a")]);

    const page = olderPage(state);
    assert.deepEqual(page, { from: "2026-10-24", to: "2026-10-30" });

    state = receive(state, page, [day("2026-10-25", "b")]);
    assert.deepEqual(state.loaded, { from: "2026-10-24", to: "2026-11-06" });
    assert.deepEqual(state.days.map((d) => d.date), ["2026-11-06", "2026-10-25"]);
    assert.deepEqual(olderPage(state), { from: "2026-10-17", to: "2026-10-23" });
  });

  test("days without entries are skipped but still count as loaded", () => {
    let state = initial("2026-11-06");
    state = receive(state, state.loaded, []);

    assert.deepEqual(state.days, []);
    assert.equal(reviewSince(state), "2026-10-31");
  });

  test("a refresh replaces the days it covers and drops deleted ones", () => {
    let state = initial("2026-11-06");
    state = receive(state, state.loaded, [day("2026-11-06", "a"), day("2026-11-05", "x")]);

    state = receive(state, state.loaded, [day("2026-11-06", "a", "b")]);

    assert.deepEqual(state.days.map((d) => [d.date, d.entries.length]), [["2026-11-06", 2]]);
  });

  test("a screen that follows today moves with it", () => {
    const state = initial("2026-11-06");

    assert.deepEqual(refreshRange(state, "2026-11-07"), { from: "2026-10-31", to: "2026-11-07" });
  });
});

describe("periods", () => {
  test("a chosen period starts at its last day and keeps going back", () => {
    let state = jump("2026-09-01", "2026-09-10", "2026-11-06");
    assert.deepEqual(state.loaded, { from: "2026-09-01", to: "2026-09-10" });
    assert.equal(state.following, false);
    assert.deepEqual(refreshRange(state, "2026-11-07"), { from: "2026-09-01", to: "2026-09-10" });

    state = receive(state, state.loaded, [day("2026-09-10", "a")]);
    assert.deepEqual(olderPage(state), { from: "2026-08-25", to: "2026-08-31" });
  });

  test("a period reaching past today stops at today and follows it", () => {
    const state = jump("2026-11-01", "2026-12-01", "2026-11-06");
    assert.deepEqual(state.loaded, { from: "2026-11-01", to: "2026-11-06" });
    assert.equal(state.following, true);
  });

  test("bad periods are refused", () => {
    assert.throws(() => jump("2026-09-10", "2026-09-01", "2026-11-06"), RangeError);
    assert.throws(() => jump("2026-9-1", "2026-09-10", "2026-11-06"), RangeError);
  });

  test("opening a search hit shows the week up to it, marked", () => {
    const state = jumpEndingAt("2026-09-10", "2026-11-06", "2026-09-10 10:00 a");
    assert.deepEqual(state.loaded, { from: "2026-09-04", to: "2026-09-10" });
    assert.equal(state.highlight, "2026-09-10 10:00 a");
  });

  test("the review starts at the first loaded day", () => {
    let state = initial("2026-11-06");
    state = receive(state, olderPage(state), []);
    assert.equal(reviewSince(state), "2026-10-24");
  });
});

describe("search", () => {
  test("clearing a search returns to the same timeline", () => {
    let state = initial("2026-11-06");
    state = receive(state, olderPage(state), [day("2026-10-25", "b")]);
    const before = state;

    state = withSearch(state, { query: "b", semantic: false, results: [] });
    assert.equal(state.search.query, "b");

    assert.deepEqual(clearSearch(state), before);
  });
});
