/**
 * What one timeline screen shows, and how it changes.
 *
 * The extension keeps one of these per screen (the side bar and each editor
 * tab); the webview only draws what it is sent. No VS Code API here, so the
 * logic runs under `node --test`.
 *
 * Dates are "YYYY-MM-DD" strings throughout. The newest day is drawn first and
 * scrolling down reaches older days.
 */

import type { Day, SearchHit } from "./cli.ts";

/** How many days a screen loads at a time. */
export const PAGE_DAYS = 7;

export interface Range {
  from: string;
  to: string;
}

export interface SearchState {
  query: string;
  semantic: boolean;
  results: SearchHit[];
}

export interface ViewState {
  /** Every day from `from` to `to` has been asked for, entries or not */
  loaded: Range;
  /** Days with a file, newest first */
  days: Day[];
  /** Whether `to` follows today, so a refresh on a later day moves with it */
  following: boolean;
  /** An entry to bring into view and mark, as "date time text" */
  highlight: string | null;
  /** A search replaces the list until it is cleared; the timeline stays as it was */
  search: SearchState | null;
}

// ---------------------------------------------------------------------------
// Dates
// ---------------------------------------------------------------------------

const DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function isDate(value: string): boolean {
  const match = DATE.exec(value);
  if (!match) {
    return false;
  }
  const [, y, m, d] = match.map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d;
}

/** Move a date by whole days. UTC arithmetic, so no daylight saving gap. */
export function addDays(value: string, days: number): string {
  const [y, m, d] = value.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}

/** Today in local time, as the CLI dates entries. */
export function localToday(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

// ---------------------------------------------------------------------------
// The timeline
// ---------------------------------------------------------------------------

/** A screen as it first opens: the last PAGE_DAYS days, following today. */
export function initial(today: string): ViewState {
  return {
    loaded: { from: addDays(today, -(PAGE_DAYS - 1)), to: today },
    days: [],
    following: true,
    highlight: null,
    search: null,
  };
}

/** The range to ask for so the screen shows a chosen period. */
export function jump(from: string, to: string, today: string): ViewState {
  if (!isDate(from) || !isDate(to)) {
    throw new RangeError(`Not a date: ${isDate(from) ? to : from}`);
  }
  if (from > to) {
    throw new RangeError(`${from} is later than ${to}`);
  }
  const end = to > today ? today : to;
  const start = from > end ? end : from;
  return { loaded: { from: start, to: end }, days: [], following: end === today, highlight: null, search: null };
}

/** A screen that shows the days up to `to`, as when a search hit is opened. */
export function jumpEndingAt(to: string, today: string, highlight: string | null = null): ViewState {
  const end = to > today ? today : to;
  return { ...jump(addDays(end, -(PAGE_DAYS - 1)), end, today), highlight };
}

/** The next older page to ask for. */
export function olderPage(state: ViewState): Range {
  return { from: addDays(state.loaded.from, -PAGE_DAYS), to: addDays(state.loaded.from, -1) };
}

/** What a refresh asks for: the same days, moving with today if the screen follows it. */
export function refreshRange(state: ViewState, today: string): Range {
  return { from: state.loaded.from, to: state.following ? today : state.loaded.to };
}

/**
 * Take in the days the CLI returned for `range`.
 *
 * Days already shown are replaced by the new copy, which may have more entries;
 * days of `range` that came back without a file are dropped, since their file
 * was deleted or emptied.
 */
export function receive(state: ViewState, range: Range, days: Day[]): ViewState {
  const inRange = (date: string) => range.from <= date && date <= range.to;
  const kept = state.days.filter((day) => !inRange(day.date));
  const merged = [...kept, ...days.filter((day) => inRange(day.date))];
  merged.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

  return {
    ...state,
    loaded: {
      from: range.from < state.loaded.from ? range.from : state.loaded.from,
      to: range.to > state.loaded.to ? range.to : state.loaded.to,
    },
    days: merged,
  };
}

/** Where a review of what the screen shows starts: the first day it has loaded. */
export function reviewSince(state: ViewState): string {
  return state.loaded.from;
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export function withSearch(state: ViewState, search: SearchState): ViewState {
  return { ...state, search };
}

/** Back to the timeline exactly as it was before the search. */
export function clearSearch(state: ViewState): ViewState {
  return { ...state, search: null };
}

/** The key that marks one entry, shared with the webview. */
export function entryKey(date: string, time: string, text: string): string {
  return `${date} ${time} ${text}`;
}
