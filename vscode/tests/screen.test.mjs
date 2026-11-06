import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { CliError } from "../src/cli.ts";
import { Screen } from "../src/screen.ts";
import { stringsFor } from "../src/strings.ts";

const TODAY = "2026-11-06";

const day = (date, ...texts) => ({
  date,
  path: `/kb/${date}.md`,
  entries: texts.map((text) => ({ date, time: "10:00", text, tags: [] })),
  content: texts.map((text) => `- 10:00 | ${text}`).join("\n"),
});

/** A CLI that answers from a table of days, and records into it. */
class FakeCli {
  constructor(days = []) {
    this.days_ = days;
    this.calls = [];
    this.failRecord = null;
    this.searchResults = [];
    this.searchGate = null;
  }

  async days(from, to) {
    this.calls.push(["days", from, to]);
    return { from, to, days: this.days_.filter((d) => from <= d.date && d.date <= to) };
  }

  async record(text) {
    this.calls.push(["record", text]);
    if (this.failRecord) throw this.failRecord;
    const existing = this.days_.find((d) => d.date === TODAY);
    const entry = { date: TODAY, time: "10:00", text, tags: [] };
    if (existing) existing.entries.push(entry);
    else this.days_.push(day(TODAY, text));
    return { entry, path: `/kb/${TODAY}.md`, notices: [{ kind: "review", message: "리뷰할 때입니다" }] };
  }

  async search(query, semantic) {
    this.calls.push(["search", query, semantic]);
    if (this.searchGate) await this.searchGate;
    return { query, mode: semantic ? "hybrid" : "keyword", cached: false, results: this.searchResults, notices: [] };
  }
}

function setup(days, earliest = "2026-01-01") {
  const cli = new FakeCli(days);
  const host = {
    posts: [],
    opened: [],
    notices: [],
    reviews: [],
    recordedCount: 0,
    post(message) { this.posts.push(message); },
    openFile(path, line) { this.opened.push([path, line]); },
    notify(notices) { this.notices.push(...notices); },
    review(since) { this.reviews.push(since); },
    widen() {},
    recorded() { this.recordedCount++; },
  };
  const screen = new Screen(host, { status: "ready", cli, earliest }, stringsFor("ko"), () => TODAY);
  const last = () => host.posts.filter((m) => m.type === "render").at(-1).model;
  return { cli, host, screen, last };
}

describe("opening", () => {
  test("shows the last seven days", async () => {
    const { screen, last, cli } = setup([day("2026-11-06", "a"), day("2026-10-01", "old")]);
    await screen.handle({ type: "ready" });

    assert.deepEqual(cli.calls, [["days", "2026-10-31", "2026-11-06"]]);
    assert.deepEqual(last().days.map((d) => d.date), ["2026-11-06"]);
    assert.equal(last().busy, null);
    assert.equal(last().hasOlder, true);
  });

  test("scrolling down loads the week before, until the earliest entries", async () => {
    const { screen, last } = setup([day("2026-11-06", "a"), day("2026-10-25", "b")], "2026-10-24");
    await screen.handle({ type: "ready" });
    await screen.handle({ type: "older" });

    assert.deepEqual(last().days.map((d) => d.date), ["2026-11-06", "2026-10-25"]);
    assert.equal(last().hasOlder, false);
  });

  test("a missing Python is explained", async () => {
    const { screen, cli, last } = setup([]);
    cli.days = async () => { throw new CliError("python_not_found", "Python not found: python"); };
    await screen.handle({ type: "ready" });

    assert.equal(last().error, stringsFor("ko").pythonNotFound);
  });
});

describe("recording", () => {
  test("records, clears the input, shows notices and the entry", async () => {
    const { screen, host, last } = setup([]);
    await screen.handle({ type: "ready" });
    await screen.handle({ type: "record", text: "새 기록 #태그" });

    assert.ok(host.posts.some((m) => m.type === "recorded"));
    assert.deepEqual(host.notices, [{ kind: "review", message: "리뷰할 때입니다" }]);
    assert.equal(host.recordedCount, 1);
    assert.equal(last().days[0].entries.at(-1).text, "새 기록 #태그");
  });

  test("a screen on an old period goes back to today to show the entry", async () => {
    const { screen, last } = setup([]);
    await screen.handle({ type: "jump", from: "2026-09-01", to: "2026-09-07" });
    await screen.handle({ type: "record", text: "x" });

    assert.deepEqual(last().loaded, { from: "2026-10-31", to: "2026-11-06" });
    assert.equal(last().days[0].date, TODAY);
  });

  test("a failure keeps the text and says why", async () => {
    const { screen, host, cli, last } = setup([]);
    cli.failRecord = new CliError("future_time", "Cannot record in the future");
    await screen.handle({ type: "record", text: "x" });

    assert.ok(!host.posts.some((m) => m.type === "recorded"));
    assert.equal(last().error, "Cannot record in the future");
  });
});

describe("periods and review", () => {
  test("quick buttons and the review start", async () => {
    const { screen, host, last } = setup([]);
    await screen.handle({ type: "quick", which: "lastWeek" });
    assert.deepEqual(last().loaded, { from: "2026-10-26", to: "2026-11-01" });

    await screen.handle({ type: "older" });
    await screen.handle({ type: "review" });
    assert.deepEqual(host.reviews, ["2026-10-19"]);
  });

  test("a bad period is reported, not loaded", async () => {
    const { screen, cli, last } = setup([]);
    await screen.handle({ type: "jump", from: "2026-09-07", to: "2026-09-01" });

    assert.equal(cli.calls.length, 0);
    assert.match(last().error, /later than/);
  });
});

describe("search", () => {
  const hits = [
    { path: "/kb/2026-09-10.md", kind: "timeline", line: 2, text: "- 10:00 | 포트", context: "", score: 1, date: "2026-09-10",
      entry: { date: "2026-09-10", time: "10:00", text: "포트", tags: [] } },
    { path: "/kb/modules/server.md", kind: "module", line: 7, text: "포트 8443", context: "", score: 1, date: null },
  ];

  test("results replace the list and clearing returns to it", async () => {
    const { screen, cli, last } = setup([day("2026-11-06", "a")]);
    cli.searchResults = hits;
    await screen.handle({ type: "ready" });
    await screen.handle({ type: "search", query: "포트", semantic: true });

    assert.deepEqual(cli.calls.at(-1), ["search", "포트", true]);
    assert.equal(last().search.results.length, 2);

    await screen.handle({ type: "clearSearch" });
    assert.equal(last().search, null);
    assert.deepEqual(last().days.map((d) => d.date), ["2026-11-06"]);
  });

  test("a timeline hit opens its week and marks the entry; a document hit opens the file", async () => {
    const { screen, cli, host, last } = setup([day("2026-09-10", "포트")]);
    cli.searchResults = hits;
    await screen.handle({ type: "search", query: "포트", semantic: false });

    await screen.handle({ type: "openHit", index: 1 });
    assert.deepEqual(host.opened, [["/kb/modules/server.md", 7]]);

    await screen.handle({ type: "openHit", index: 0 });
    assert.deepEqual(last().loaded, { from: "2026-09-04", to: "2026-09-10" });
    assert.equal(last().highlight, "2026-09-10 10:00 포트");
    assert.equal(last().search, null);
  });

  test("an answer that comes after the person moved on is dropped", async () => {
    const { screen, cli, last } = setup([]);
    let release;
    cli.searchGate = new Promise((resolve) => (release = resolve));
    cli.searchResults = hits;

    const searching = screen.handle({ type: "search", query: "포트", semantic: true });
    await screen.handle({ type: "latest" });
    release();
    await searching;

    assert.equal(last().search, null);
  });
});

describe("refresh", () => {
  test("a refresh during a load runs after it", async () => {
    const { screen, cli } = setup([]);
    let release;
    const gate = new Promise((resolve) => (release = resolve));
    const days = cli.days.bind(cli);
    cli.days = async (from, to) => { await gate; return days(from, to); };

    const loading = screen.handle({ type: "ready" });
    await screen.refresh();
    release();
    await loading;

    assert.equal(cli.calls.filter((call) => call[0] === "days").length, 2);
  });
});
