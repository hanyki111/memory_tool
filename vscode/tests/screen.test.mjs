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
    this.plans = {};
    this.planCalls = [];
    this.planFailure = null;
    this.planSetGate = null;
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

  // ---- daily plans, kept apart from `calls` so the timeline tests stay as they were

  planOf(date) {
    const tasks = this.plans[date] ?? [];
    return {
      date,
      path: `/kb/plans/${date}.md`,
      exists: date in this.plans,
      tasks: tasks.map((task) => ({ ...task })),
      progress: { done: tasks.filter((t) => t.done).length, total: tasks.length },
      recurring: null,
    };
  }

  async plan(date) {
    this.planCalls.push(["plan", date]);
    if (this.planFailure) throw this.planFailure;
    return this.planOf(date ?? TODAY);
  }

  addTask(text) {
    const tasks = (this.plans[TODAY] ??= []);
    tasks.unshift({ line: 5, text, done: false, time: null });
    tasks.forEach((task, i) => (task.line = 5 + i));
    return tasks[0];
  }

  async planAdd(text) {
    this.planCalls.push(["add", text]);
    const task = this.addTask(text);
    return { task, plan: this.planOf(TODAY) };
  }

  async planSet(task, done) {
    this.planCalls.push([done ? "done" : "undo", task.line, task.text]);
    if (this.planSetGate) await this.planSetGate;
    const found = (this.plans[TODAY] ?? []).find((t) => t.line === task.line && t.text === task.text);
    if (!found) throw new CliError("not_found", "No task on that line");
    found.done = done;
    found.time = done ? "10:30" : null;
    const notices = done ? [] : [{ kind: "plan", message: "엔트리를 찾지 못했습니다" }];
    return { task: found, plan: this.planOf(TODAY), notices };
  }

  async planCarryover(tasks) {
    this.planCalls.push(["carryover", ...tasks]);
    for (const text of [...tasks].reverse()) this.addTask(text);
    return { from: "2026-11-05", carried: tasks, skipped: [], missing: [], plan: this.planOf(TODAY) };
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
    picks: [],
    pickAnswer: undefined,
    async pickMany(items, title) { this.picks.push([items, title]); return this.pickAnswer; },
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
    await screen.handle({ type: "reviewFrom" });
    assert.deepEqual(host.reviews, ["2026-10-19"]);
  });

  test("the plain review ignores what the screen has loaded", async () => {
    const { screen, host } = setup([]);
    await screen.handle({ type: "quick", which: "lastWeek" });
    await screen.handle({ type: "older" });

    await screen.handle({ type: "review" });

    assert.deepEqual(host.reviews, [null]);
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

describe("today's plan", () => {
  const task = (line, text, done = false) => ({ line, text, done, time: done ? "09:00" : null });

  test("opening reads today's plan along with the timeline", async () => {
    const { screen, cli, last } = setup([]);
    cli.plans[TODAY] = [task(5, "문서 쓰기"), task(6, "리뷰", true)];
    await screen.handle({ type: "ready" });

    assert.deepEqual(cli.planCalls, [["plan", null]]);
    assert.equal(last().plan.status, "ready");
    assert.deepEqual(last().plan.plan.tasks.map((t) => t.text), ["문서 쓰기", "리뷰"]);
    assert.deepEqual(last().plan.plan.progress, { done: 1, total: 2 });
  });

  test("adding a task shows it and clears the box", async () => {
    const { screen, cli, host, last } = setup([]);
    await screen.handle({ type: "ready" });
    await screen.handle({ type: "planAdd", text: "새 작업" });

    assert.deepEqual(cli.planCalls.at(-1), ["add", "새 작업"]);
    assert.deepEqual(last().plan.plan.tasks.map((t) => t.text), ["새 작업"]);
    assert.ok(host.posts.some((m) => m.type === "planAdded"));
  });

  test("checking a task completes it by line and text, and reloads the timeline", async () => {
    const { screen, cli, host, last } = setup([]);
    cli.plans[TODAY] = [task(5, "문서 쓰기")];
    await screen.handle({ type: "ready" });
    const daysBefore = cli.calls.filter((c) => c[0] === "days").length;

    await screen.handle({ type: "planSet", line: 5, text: "문서 쓰기", done: true });

    assert.deepEqual(cli.planCalls[1], ["done", 5, "문서 쓰기"]);
    assert.equal(last().plan.plan.tasks[0].done, true);
    assert.equal(last().plan.busy, false);
    assert.equal(cli.calls.filter((c) => c[0] === "days").length, daysBefore + 1);
    assert.equal(host.recordedCount, 1);
  });

  test("unchecking undoes it and passes on what the CLI says", async () => {
    const { screen, cli, host, last } = setup([]);
    cli.plans[TODAY] = [task(5, "문서 쓰기", true)];
    await screen.handle({ type: "ready" });

    await screen.handle({ type: "planSet", line: 5, text: "문서 쓰기", done: false });

    assert.deepEqual(cli.planCalls[1], ["undo", 5, "문서 쓰기"]);
    assert.equal(last().plan.plan.tasks[0].done, false);
    assert.deepEqual(host.notices.map((n) => n.kind), ["plan"]);
  });

  test("the controls wait while a change is made", async () => {
    const { screen, cli, last } = setup([]);
    cli.plans[TODAY] = [task(5, "가"), task(6, "나")];
    await screen.handle({ type: "ready" });
    let release;
    cli.planSetGate = new Promise((resolve) => (release = resolve));

    const first = screen.handle({ type: "planSet", line: 5, text: "가", done: true });
    assert.equal(last().plan.busy, true);
    await screen.handle({ type: "planSet", line: 6, text: "나", done: true });
    release();
    await first;

    assert.deepEqual(cli.planCalls.filter((c) => c[0] === "done"), [["done", 5, "가"]]);
  });

  test("a plan changed on disk since is read again instead of changing another task", async () => {
    const { screen, cli, last } = setup([]);
    cli.plans[TODAY] = [task(5, "가")];
    await screen.handle({ type: "ready" });
    cli.plans[TODAY] = [task(5, "다른 일"), task(6, "가")];

    await screen.handle({ type: "planSet", line: 5, text: "가", done: true });

    assert.ok(last().plan.error);
    assert.deepEqual(
      last().plan.plan.tasks.map((t) => [t.line, t.text, t.done]),
      [[5, "다른 일", false], [6, "가", false]]
    );
  });

  test("carrying over offers yesterday's unfinished tasks that today lacks", async () => {
    const { screen, cli, host, last } = setup([]);
    cli.plans["2026-11-05"] = [task(5, "가"), task(6, "나"), task(7, "다", true)];
    cli.plans[TODAY] = [task(5, "나")];
    await screen.handle({ type: "ready" });
    host.pickAnswer = ["가"];

    await screen.handle({ type: "planCarryover" });

    assert.deepEqual(host.picks.map(([items]) => items), [["가"]]);
    assert.deepEqual(cli.planCalls.at(-1), ["carryover", "가"]);
    assert.deepEqual(last().plan.plan.tasks.map((t) => t.text), ["가", "나"]);
  });

  test("nothing to carry over, or nothing chosen, changes nothing", async () => {
    const { screen, cli, host } = setup([]);
    await screen.handle({ type: "ready" });
    await screen.handle({ type: "planCarryover" });
    assert.deepEqual(host.picks, []);
    assert.deepEqual(host.notices.map((n) => n.kind), ["plan"]);

    cli.plans["2026-11-05"] = [task(5, "가")];
    host.pickAnswer = undefined;
    await screen.handle({ type: "planCarryover" });
    assert.equal(host.picks.length, 1);
    assert.ok(!cli.planCalls.some((c) => c[0] === "carryover"));
  });

  test("a refresh reads the plan again", async () => {
    const { screen, cli, last } = setup([]);
    await screen.handle({ type: "ready" });
    cli.plans[TODAY] = [task(5, "터미널에서 추가")];

    await screen.refresh();

    assert.deepEqual(last().plan.plan.tasks.map((t) => t.text), ["터미널에서 추가"]);
  });

  test("open file opens the plan, when there is one", async () => {
    const { screen, cli, host } = setup([]);
    await screen.handle({ type: "ready" });
    await screen.handle({ type: "planOpen" });
    assert.deepEqual(host.opened, []);

    cli.plans[TODAY] = [task(5, "가")];
    await screen.refresh();
    await screen.handle({ type: "planOpen" });
    assert.deepEqual(host.opened, [[`/kb/plans/${TODAY}.md`, 1]]);
  });

  test("an older CLI is told apart, and the timeline still works", async () => {
    const { screen, cli, last } = setup([day("2026-11-06", "a")]);
    cli.planFailure = new CliError("outdated", "update");
    await screen.handle({ type: "ready" });

    assert.equal(last().plan.status, "outdated");
    assert.equal(last().plan.error, null);
    assert.deepEqual(last().days.map((d) => d.date), ["2026-11-06"]);

    await screen.handle({ type: "planAdd", text: "가" });
    assert.ok(!cli.planCalls.some((c) => c[0] === "add"));
  });
});
