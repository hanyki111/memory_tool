/**
 * Timeline file naming and entry formatting.
 *
 * Kept free of any `obsidian` import so it stays directly testable under
 * `node --test`; everything that touches the vault lives in directWriter.ts.
 *
 * Every function here mirrors memory_tool/core/timeline.py. When that file
 * changes, these are the counterparts to re-check:
 *
 *   timeline_filename()      -> filenameFor()
 *   Timeline.candidate_paths -> candidatePaths()
 *   Timeline.format_entry    -> formatEntry()
 *   Timeline.write_timeline  -> headerFor() and the trailing newline
 */

// Explicit .ts so Node's ESM loader can run this module directly in tests.
import { underBase } from "../paths.ts";

/** How a timeline file is named inside its YYYY-MM folder. */
export type FilenameLayout = "day" | "date";

/** How tags are embedded in an entry line. */
export type TagFormat = "bracket" | "hashtag";

export const FILENAME_LAYOUTS: FilenameLayout[] = ["day", "date"];
export const DEFAULT_FILENAME_LAYOUT: FilenameLayout = "day";
export const DEFAULT_TAG_FORMAT: TagFormat = "bracket";

/**
 * What the plugin setting can hold: a fixed layout, or "auto" to work it out
 * from the knowledge base itself.
 */
export type FilenameLayoutSetting = FilenameLayout | "auto";

/** Where a resolved layout came from, so the user can be told. */
export type LayoutSource = "setting" | "config" | "files" | "default";

/** "2026-08-17.md" */
const DATE_FILE = /^\d{4}-\d{2}-\d{2}\.md$/;
/** "17.md" -- a day only means something together with its YYYY-MM folder. */
const DAY_FILE = /^\d{1,2}\.md$/;
/** "2026-08" */
const MONTH_DIR = /^\d{4}-\d{2}$/;

/** Settings read out of the knowledge base's config.yaml. */
export interface TimelineConfig {
  filenameLayout: FilenameLayout;
  tagFormat: TagFormat;
}

export const DEFAULT_TIMELINE_CONFIG: TimelineConfig = {
  filenameLayout: DEFAULT_FILENAME_LAYOUT,
  tagFormat: DEFAULT_TAG_FORMAT,
};

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** "2026-08-17" */
export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** "2026-08" */
export function yearMonth(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

/** "14:30" */
export function hourMinute(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Filename for a timeline date. Mirrors `timeline_filename`. */
export function filenameFor(date: Date, layout: FilenameLayout): string {
  return layout === "date" ? `${isoDate(date)}.md` : `${pad(date.getDate())}.md`;
}

/** First line of a new timeline file. */
export function headerFor(date: Date): string {
  return `# ${isoDate(date)} Timeline`;
}

/**
 * Every location a timeline file for this date could already occupy.
 *
 * Mirrors `Timeline.candidate_paths`: both directory structures (daily/ and the
 * pre-migration flat layout) crossed with both filename layouts, most current
 * first. Checking all four is what keeps a day's entries from being split
 * across two differently-named files when the naming setting has changed.
 */
export function candidatePaths(basePrefix: string, date: Date): string[] {
  const paths: string[] = [];
  for (const dir of timelineMonthDirs(basePrefix, date)) {
    for (const layout of ["date", "day"] as FilenameLayout[]) {
      paths.push(`${dir}/${filenameFor(date, layout)}`);
    }
  }
  return paths;
}

/** Directory a new timeline file for this date belongs in. */
export function timelineDir(basePrefix: string, date: Date): string {
  return underBase(basePrefix, "timeline", "daily", yearMonth(date));
}

/** Both month folders a date could have files in, most current first. */
export function timelineMonthDirs(basePrefix: string, date: Date): string[] {
  const ym = yearMonth(date);
  return [
    underBase(basePrefix, "timeline", "daily", ym),
    underBase(basePrefix, "timeline", ym),
  ];
}

/** The folders that hold month folders, most current first. */
export function timelineRootDirs(basePrefix: string): string[] {
  return [underBase(basePrefix, "timeline", "daily"), underBase(basePrefix, "timeline")];
}

/** Keep only "YYYY-MM" names, newest first. */
export function sortMonthDirs(names: string[]): string[] {
  return names.filter((n) => MONTH_DIR.test(n)).sort().reverse();
}

/**
 * Work out which layout a knowledge base already uses from its filenames.
 *
 * This is the safety net for a config.yaml the plugin cannot read -- on a phone
 * the file may simply not have been synced. Without it the plugin falls back to
 * the Python default ("day") and writes 20.md into a knowledge base whose other
 * 200 files are named 2026-08-20.md, so the day's entries land in a file no
 * Calendar plugin and no other entry shares.
 *
 * The majority wins; a tie resolves to "date", which is the only layout a
 * half-finished `mtimeline migrate` produces a tie during.
 *
 * @param names Bare filenames from one month folder (no directory part)
 * @returns The layout in use, or null when nothing in the list is a timeline file
 */
export function layoutFromFilenames(names: string[]): FilenameLayout | null {
  let date = 0;
  let day = 0;

  for (const name of names) {
    if (DATE_FILE.test(name)) date += 1;
    else if (DAY_FILE.test(name)) day += 1;
  }

  if (date === 0 && day === 0) return null;
  return day > date ? "day" : "date";
}

/**
 * Format one entry line. Mirrors `Timeline.format_entry`.
 *
 * Bracket tags are prepended, hashtags appended -- that asymmetry is in the
 * Python and is preserved here so both writers produce identical files.
 */
export function formatEntry(
  date: Date,
  message: string,
  tags: string[] = [],
  tagFormat: TagFormat = DEFAULT_TAG_FORMAT
): string {
  const time = hourMinute(date);
  const clean = tags.map((t) => t.trim()).filter((t) => t.length > 0);

  if (clean.length === 0) return `- ${time} | ${message}`;

  if (tagFormat === "hashtag") {
    const tagStr = clean.map((t) => `#${t.replace(/ /g, "-")}`).join(" ");
    return `- ${time} | ${message} ${tagStr}`;
  }

  const tagStr = clean.map((t) => `[${t.replace(/ /g, "-")}]`).join(" ");
  return `- ${time} | ${tagStr} ${message}`;
}

/** Collapse a message to the single line an entry must occupy. */
export function sanitizeMessage(message: string): string {
  return message.replace(/[\r\n]+/g, " ").trim();
}

/**
 * Append an entry to existing file content, keeping exactly one trailing
 * newline. Mirrors the tail of `write_timeline`.
 */
export function appendEntry(existing: string, entry: string): string {
  return `${existing.replace(/\n+$/, "")}\n${entry}\n`;
}

/** Full body for a timeline file that does not exist yet. */
export function newFileBody(date: Date, entry: string): string {
  return `${headerFor(date)}\n${entry}\n`;
}

/**
 * The layout config.yaml actually states, or null when it states none.
 *
 * The null matters: "the file does not say" and "the file says day" have to be
 * told apart, because only the first one may be overruled by what is on disk.
 */
export function configuredFilenameLayout(parsed: unknown): FilenameLayout | null {
  const layout = (parsed ?? ({} as any))?.timeline?.filename;
  return layout === "date" || layout === "day" ? layout : null;
}

/** Pick the timeline settings out of a parsed config.yaml. */
export function timelineConfigFrom(parsed: unknown): TimelineConfig {
  const root = (parsed ?? {}) as Record<string, any>;
  const tagFmt = root?.tag?.storage_format;

  return {
    filenameLayout: configuredFilenameLayout(parsed) ?? DEFAULT_FILENAME_LAYOUT,
    tagFormat: tagFmt === "hashtag" || tagFmt === "bracket" ? tagFmt : DEFAULT_TAG_FORMAT,
  };
}
