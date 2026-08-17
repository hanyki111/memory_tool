/**
 * Python-free timeline capture.
 *
 * Recording through the CLI costs a full Python interpreter start -- measured at
 * ~1.6s on a normal desktop, against a product promise of 0.5s. Appending the
 * line ourselves takes single-digit milliseconds, so capture stops paying for an
 * interpreter it barely uses.
 *
 * The trade-off is that we now own the file format; format.ts holds that
 * knowledge and documents which Python functions it mirrors.
 *
 * Writes go through the *adapter* rather than the vault API on purpose: the
 * knowledge base usually lives in `.memory/`, and Obsidian's vault index skips
 * dot-folders entirely. The adapter is a raw filesystem view with no such blind
 * spot.
 */

import { DataAdapter, parseYaml } from "obsidian";
import { underBase } from "../paths";
import {
  DEFAULT_TIMELINE_CONFIG,
  TimelineConfig,
  appendEntry,
  candidatePaths,
  filenameFor,
  formatEntry,
  newFileBody,
  sanitizeMessage,
  timelineConfigFrom,
  timelineDir,
} from "./format";

export * from "./format";

/** Result of a direct write, for the caller's notice and index bookkeeping. */
export interface RecordResult {
  /** Vault-relative path the entry landed in. */
  path: string;
  /** The formatted line, exactly as written. */
  entry: string;
  /** True when this call created the file. */
  created: boolean;
}

/**
 * Read the timeline settings out of the knowledge base's config.yaml.
 *
 * A missing or unreadable config is not an error: memory_tool falls back to the
 * same defaults, so capture keeps working on a bare knowledge base.
 */
export async function readTimelineConfig(
  adapter: DataAdapter,
  basePrefix: string
): Promise<TimelineConfig> {
  const path = underBase(basePrefix, "config.yaml");

  try {
    if (!(await adapter.exists(path))) return { ...DEFAULT_TIMELINE_CONFIG };
    return timelineConfigFrom(parseYaml(await adapter.read(path)));
  } catch {
    return { ...DEFAULT_TIMELINE_CONFIG };
  }
}

/**
 * Append an entry to today's timeline file, creating it when needed.
 *
 * Appends to whichever file already holds this date -- in any of the four
 * supported layouts -- and only falls back to the configured layout when none
 * exists. Writing the configured name unconditionally would strand entries in a
 * second file whenever the knowledge base predates the current setting.
 *
 * @param adapter    Vault adapter (raw filesystem view, dot-folders included)
 * @param basePrefix Vault-relative knowledge base prefix ("" = vault root)
 * @param message    Entry text; newlines are collapsed to keep one line per entry
 * @param tags       Optional tags
 * @param when       Timestamp, defaulting to now (injectable for tests)
 */
export async function recordDirect(
  adapter: DataAdapter,
  basePrefix: string,
  message: string,
  tags: string[] = [],
  when: Date = new Date()
): Promise<RecordResult> {
  const text = sanitizeMessage(message);
  if (!text) throw new Error("Cannot record an empty message.");

  const config = await readTimelineConfig(adapter, basePrefix);

  // Prefer a file that already exists for this date, whatever it is named.
  let path: string | null = null;
  for (const candidate of candidatePaths(basePrefix, when)) {
    if (await adapter.exists(candidate)) {
      path = candidate;
      break;
    }
  }

  const created = path === null;
  if (path === null) {
    const dir = timelineDir(basePrefix, when);
    path = `${dir}/${filenameFor(when, config.filenameLayout)}`;
    if (!(await adapter.exists(dir))) {
      await adapter.mkdir(dir);
    }
  }

  const entry = formatEntry(when, text, tags, config.tagFormat);
  const body = created
    ? newFileBody(when, entry)
    : appendEntry(await adapter.read(path), entry);

  await adapter.write(path, body);

  return { path, entry, created };
}
