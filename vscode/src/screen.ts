/**
 * One timeline screen: the side bar view or an editor tab.
 *
 * It answers the webview's messages by calling the CLI and sending back what to
 * draw. Everything VS Code does for it goes through `ScreenHost`, so the logic
 * runs under `node --test` with a fake host.
 */

import { CliError, OUTDATED, PYTHON_NOT_FOUND } from "./cli.ts";
import type { DailyPlan, MemoryToolCli, Notice, PlanTask, SearchHit } from "./cli.ts";
import {
  addDays,
  clearSearch,
  entryKey,
  hasOlder,
  initial,
  jump,
  jumpEndingAt,
  localToday,
  olderPage,
  quickRange,
  receive,
  refreshRange,
  reviewSince,
  withSearch,
} from "./state.ts";
import type { Quick, Range, ViewState } from "./state.ts";
import type { Strings } from "./strings.ts";

/** What the screen needs from the extension. */
export interface ScreenHost {
  post(message: unknown): void;
  openFile(path: string, line: number): void;
  notify(notices: Notice[]): void;
  review(since: string | null): void;
  widen(): void;
  /** Tell the other screens that the timeline changed */
  recorded(): void;
  /** Let the person choose some of the items; undefined when cancelled */
  pickMany(items: string[], title: string): Promise<string[] | undefined>;
}

/** The knowledge base a screen works on, shared by every screen of a window. */
export interface Session {
  status: "ready" | "nobase" | "nofolder";
  cli: MemoryToolCli | null;
  earliest: string | null;
}

type Busy = "loading" | "searching" | "recording" | null;

/** Today's plan as the screen shows it. */
export interface PlanView {
  /** "outdated": the CLI has no `mplan daily --json` */
  status: "loading" | "ready" | "outdated";
  plan: DailyPlan | null;
  /** A change is being made; the controls wait */
  busy: boolean;
  error: string | null;
}

export class Screen {
  private state: ViewState;
  private busy: Busy = null;
  private error: string | null = null;
  /** Bumped by every change of what the screen shows, so stale answers are dropped */
  private generation = 0;
  private refreshQueued = false;
  private planView: PlanView = { status: "loading", plan: null, busy: false, error: null };
  /** Bumped by every plan read, so an older answer never replaces a newer one */
  private planGeneration = 0;

  private readonly host: ScreenHost;
  private session: Session;
  private readonly strings: Strings;
  private readonly today: () => string;

  constructor(host: ScreenHost, session: Session, strings: Strings, today: () => string = () => localToday()) {
    this.host = host;
    this.session = session;
    this.strings = strings;
    this.today = today;
    this.state = initial(today());
  }

  /** The current state, for tests. */
  get view(): ViewState {
    return this.state;
  }

  /** The plan as shown, for tests. */
  get plan(): PlanView {
    return this.planView;
  }

  /** Start over on another session, as after the setting or the folder changed. */
  async restart(session: Session): Promise<void> {
    this.session = session;
    this.state = initial(this.today());
    this.generation++;
    this.busy = null;
    this.planView = { status: "loading", plan: null, busy: false, error: null };
    await Promise.all([this.load(this.state.loaded), this.loadPlan()]);
  }

  async handle(message: { type: string; [key: string]: unknown }): Promise<void> {
    switch (message.type) {
      case "ready":
        this.draw();
        await Promise.all([this.load(this.state.loaded), this.loadPlan()]);
        return;
      case "older":
        return this.older();
      case "jump":
        return this.jumpTo(String(message.from), String(message.to));
      case "quick": {
        const range = quickRange(message.which as Quick, this.today());
        return this.jumpTo(range.from, range.to);
      }
      case "latest":
        return this.show(initial(this.today()));
      case "record":
        return this.record(String(message.text));
      case "search":
        return this.search(String(message.query), Boolean(message.semantic));
      case "clearSearch":
        this.state = clearSearch(this.state);
        this.error = null;
        this.draw();
        return;
      case "openHit":
        return this.openHit(Number(message.index));
      case "openFile":
        this.host.openFile(String(message.path), Number(message.line) || 1);
        return;
      case "review":
        this.host.review(null);
        return;
      case "reviewFrom":
        this.host.review(reviewSince(this.state));
        return;
      case "widen":
        this.host.widen();
        return;
      case "planAdd":
        return this.planAdd(String(message.text ?? ""));
      case "planSet":
        return this.planSet(
          { line: Number(message.line), text: String(message.text) },
          Boolean(message.done)
        );
      case "planCarryover":
        return this.planCarryover();
      case "planOpen":
        if (this.planView.plan?.exists) {
          this.host.openFile(this.planView.plan.path, 1);
        }
        return;
    }
  }

  /** Read the shown days and today's plan again, as after a file changed on disk. */
  async refresh(): Promise<void> {
    if (this.session.status !== "ready") {
      return;
    }
    const plan = this.planView.busy ? Promise.resolve() : this.loadPlan();
    if (this.busy) {
      this.refreshQueued = true;
      await plan;
      return;
    }
    await Promise.all([this.load(refreshRange(this.state, this.today()), false), plan]);
  }

  // ---- actions ------------------------------------------------------------

  private async older(): Promise<void> {
    if (this.busy || this.state.search || !hasOlder(this.state, this.session.earliest)) {
      return;
    }
    await this.load(olderPage(this.state));
  }

  private async jumpTo(from: string, to: string): Promise<void> {
    try {
      await this.show(jump(from, to, this.today()));
    } catch (error) {
      this.error = (error as Error).message;
      this.draw();
    }
  }

  private async show(state: ViewState): Promise<void> {
    this.state = state;
    this.generation++;
    this.busy = null;
    await this.load(state.loaded);
  }

  private async record(text: string): Promise<void> {
    const cli = this.session.cli;
    if (!cli || this.busy === "recording" || !text.trim()) {
      return;
    }

    this.busy = "recording";
    this.error = null;
    this.draw();
    try {
      const result = await cli.record(text);
      this.busy = null;
      this.host.post({ type: "recorded" });
      this.host.notify(result.notices ?? []);
      this.host.recorded();

      // A screen showing an old period jumps back to today to show the entry.
      if (!this.state.following || this.state.search) {
        await this.show(initial(this.today()));
      } else {
        await this.refresh();
      }
    } catch (error) {
      this.busy = null;
      this.error = this.describe(error);
      this.draw();
    }
  }

  private async search(query: string, semantic: boolean): Promise<void> {
    const cli = this.session.cli;
    if (!cli || !query.trim()) {
      return;
    }

    const generation = ++this.generation;
    this.state = withSearch(this.state, { query, semantic, results: [] });
    this.busy = "searching";
    this.error = null;
    this.draw();
    try {
      const result = await cli.search(query, semantic);
      if (generation !== this.generation) return;
      this.state = withSearch(this.state, { query, semantic, results: result.results });
      this.host.notify(result.notices ?? []);
    } catch (error) {
      if (generation !== this.generation) return;
      this.error = this.describe(error);
    }
    this.busy = null;
    this.draw();
  }

  private async openHit(index: number): Promise<void> {
    const hit: SearchHit | undefined = this.state.search?.results[index];
    if (!hit) {
      return;
    }

    if (hit.kind === "timeline" && hit.entry) {
      const { date, time, text } = hit.entry;
      await this.show(jumpEndingAt(date, this.today(), entryKey(date, time, text)));
      return;
    }
    this.host.openFile(hit.path, hit.line || 1);
  }

  // ---- today's plan ------------------------------------------------------

  private async loadPlan(): Promise<void> {
    const cli = this.session.cli;
    if (!cli) {
      return;
    }
    const generation = ++this.planGeneration;
    try {
      const plan = await cli.plan(null);
      if (generation !== this.planGeneration) return;
      this.planView = { ...this.planView, status: "ready", plan, error: null };
    } catch (error) {
      if (generation !== this.planGeneration) return;
      this.planView = this.planFailed(error);
    }
    this.draw();
  }

  private planFailed(error: unknown): PlanView {
    if (error instanceof CliError && error.code === OUTDATED) {
      return { status: "outdated", plan: null, busy: false, error: null };
    }
    return { ...this.planView, status: this.planView.plan ? "ready" : "loading", busy: false, error: this.describe(error) };
  }

  /** Make a change to today's plan, then show the plan it returns. */
  private async changePlan(
    change: (cli: MemoryToolCli) => Promise<{ plan: DailyPlan; notices?: Notice[] }>,
    timelineChanged: boolean
  ): Promise<void> {
    const cli = this.session.cli;
    if (!cli || this.planView.busy || this.planView.status !== "ready") {
      return;
    }
    this.planView = { ...this.planView, busy: true, error: null };
    this.draw();
    // A read started before this change would show the plan without it.
    this.planGeneration++;
    try {
      const result = await change(cli);
      this.planView = { status: "ready", plan: result.plan, busy: false, error: null };
      this.host.notify(result.notices ?? []);
    } catch (error) {
      this.planView = this.planFailed(error);
      this.draw();
      // The plan may have changed on disk since it was read: show it as it is
      // now, still saying why nothing was changed.
      if (error instanceof CliError && error.code === "not_found") {
        const reason = this.planView.error;
        await this.loadPlan();
        this.planView = { ...this.planView, error: reason };
        this.draw();
      }
      return;
    }
    this.draw();
    this.host.recorded();
    if (timelineChanged) {
      await this.refresh();
    }
  }

  private async planAdd(text: string): Promise<void> {
    if (!text.trim()) {
      return;
    }
    await this.changePlan(async (cli) => {
      const result = await cli.planAdd(text);
      this.host.post({ type: "planAdded" });
      return result;
    }, false);
  }

  private async planSet(task: { line: number; text: string }, done: boolean): Promise<void> {
    await this.changePlan((cli) => cli.planSet(task, done), true);
  }

  /** Choose among yesterday's unfinished tasks, and copy them into today's plan. */
  private async planCarryover(): Promise<void> {
    const cli = this.session.cli;
    if (!cli || this.planView.busy || this.planView.status !== "ready") {
      return;
    }
    let yesterday: DailyPlan;
    try {
      yesterday = await cli.plan(addDays(this.today(), -1));
    } catch (error) {
      this.planView = this.planFailed(error);
      this.draw();
      return;
    }

    const present = new Set((this.planView.plan?.tasks ?? []).map((task: PlanTask) => task.text));
    const open = yesterday.tasks.filter((task) => !task.done && !present.has(task.text)).map((task) => task.text);
    if (!open.length) {
      this.host.notify([{ kind: "plan", message: this.strings.planNothingToCarry }]);
      return;
    }

    const chosen = await this.host.pickMany(open, this.strings.planCarryoverTitle);
    if (!chosen?.length) {
      return;
    }
    await this.changePlan((cli) => cli.planCarryover(chosen), false);
  }

  // ---- loading and drawing ----------------------------------------------

  private async load(range: Range, showBusy = true): Promise<void> {
    const cli = this.session.cli;
    if (!cli) {
      this.draw();
      return;
    }

    const generation = this.generation;
    if (showBusy) {
      this.busy = "loading";
      this.draw();
    }
    try {
      const result = await cli.days(range.from, range.to);
      if (generation !== this.generation) return;
      this.state = receive(this.state, range, result.days);
      this.error = null;
    } catch (error) {
      if (generation !== this.generation) return;
      this.error = this.describe(error);
    }
    this.busy = null;
    this.draw();

    if (this.refreshQueued) {
      this.refreshQueued = false;
      await this.refresh();
    }
  }

  private describe(error: unknown): string {
    if (error instanceof CliError && error.code === PYTHON_NOT_FOUND) {
      return this.strings.pythonNotFound;
    }
    return error instanceof Error ? error.message : String(error);
  }

  private draw(): void {
    this.host.post({
      type: "render",
      model: {
        status: this.session.status,
        days: this.state.days,
        loaded: this.state.loaded,
        following: this.state.following,
        highlight: this.state.highlight,
        hasOlder: hasOlder(this.state, this.session.earliest),
        search: this.state.search,
        busy: this.busy,
        error: this.error,
        plan: this.planView,
      },
    });
  }
}
