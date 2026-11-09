/**
 * One timeline screen: the side bar view or an editor tab.
 *
 * It answers the webview's messages by calling the CLI and sending back what to
 * draw. Everything VS Code does for it goes through `ScreenHost`, so the logic
 * runs under `node --test` with a fake host.
 */

import { CliError, PYTHON_NOT_FOUND } from "./cli.ts";
import type { MemoryToolCli, Notice, SearchHit } from "./cli.ts";
import {
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
}

/** The knowledge base a screen works on, shared by every screen of a window. */
export interface Session {
  status: "ready" | "nobase" | "nofolder";
  cli: MemoryToolCli | null;
  earliest: string | null;
}

type Busy = "loading" | "searching" | "recording" | null;

export class Screen {
  private state: ViewState;
  private busy: Busy = null;
  private error: string | null = null;
  /** Bumped by every change of what the screen shows, so stale answers are dropped */
  private generation = 0;
  private refreshQueued = false;

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

  /** Start over on another session, as after the setting or the folder changed. */
  async restart(session: Session): Promise<void> {
    this.session = session;
    this.state = initial(this.today());
    this.generation++;
    this.busy = null;
    await this.load(this.state.loaded);
  }

  async handle(message: { type: string; [key: string]: unknown }): Promise<void> {
    switch (message.type) {
      case "ready":
        this.draw();
        return this.load(this.state.loaded);
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
    }
  }

  /** Read the shown days again, as after the timeline changed on disk. */
  async refresh(): Promise<void> {
    if (this.session.status !== "ready") {
      return;
    }
    if (this.busy) {
      this.refreshQueued = true;
      return;
    }
    await this.load(refreshRange(this.state, this.today()), false);
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
      },
    });
  }
}
