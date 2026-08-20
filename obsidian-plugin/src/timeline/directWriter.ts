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
  DEFAULT_FILENAME_LAYOUT,
  DEFAULT_TIMELINE_CONFIG,
  FilenameLayout,
  FilenameLayoutSetting,
  LayoutSource,
  TimelineConfig,
  appendEntry,
  candidatePaths,
  configuredFilenameLayout,
  filenameFor,
  formatEntry,
  layoutFromFilenames,
  newFileBody,
  sanitizeMessage,
  sortMonthDirs,
  timelineConfigFrom,
  timelineDir,
  timelineMonthDirs,
  timelineRootDirs,
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
  /** Filename layout used, and where that decision came from. */
  layout: LayoutResolution;
}

/** A settled filename layout together with the reason it was chosen. */
export interface LayoutResolution {
  layout: FilenameLayout;
  source: LayoutSource;
}

/** Per-call options for {@link recordDirect}. */
export interface RecordOptions {
  tags?: string[];
  /** Timestamp, defaulting to now (injectable for tests). */
  when?: Date;
  /** Plugin setting; "auto" consults config.yaml and then the existing files. */
  layoutSetting?: FilenameLayoutSetting;
}

/** Bare filename of a vault path. */
function basename(path: string): string {
  return path.split("/").filter(Boolean).pop() ?? path;
}

/**
 * Parse the knowledge base's config.yaml, or null when there is nothing to read.
 *
 * Null covers three cases the callers treat alike -- no file, no permission,
 * unparseable YAML -- but never "the file exists and says nothing", which is a
 * parsed empty object. That distinction is what lets the layout fall through to
 * the files on disk only when the config genuinely could not be consulted.
 */
export async function readParsedConfig(
  adapter: DataAdapter,
  basePrefix: string
): Promise<unknown | null> {
  const path = underBase(basePrefix, "config.yaml");

  try {
    if (!(await adapter.exists(path))) return null;
    return parseYaml(await adapter.read(path));
  } catch {
    return null;
  }
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
  const parsed = await readParsedConfig(adapter, basePrefix);
  return parsed === null ? { ...DEFAULT_TIMELINE_CONFIG } : timelineConfigFrom(parsed);
}

/**
 * Which layout the knowledge base's own files already use.
 *
 * Looks in this month's folder first and falls back to the newest month folder
 * that has files, so a knowledge base opened on the 1st of a month still gets
 * an answer. Returns null only when no timeline file can be found at all.
 */
export async function inferFilenameLayout(
  adapter: DataAdapter,
  basePrefix: string,
  when: Date
): Promise<FilenameLayout | null> {
  const namesIn = async (dir: string): Promise<string[]> => {
    try {
      if (!(await adapter.exists(dir))) return [];
      return (await adapter.list(dir)).files.map(basename);
    } catch {
      return [];
    }
  };

  for (const dir of timelineMonthDirs(basePrefix, when)) {
    const found = layoutFromFilenames(await namesIn(dir));
    if (found) return found;
  }

  // Nothing this month: fall back to the most recent month that has files.
  for (const root of timelineRootDirs(basePrefix)) {
    let folders: string[];
    try {
      if (!(await adapter.exists(root))) continue;
      folders = (await adapter.list(root)).folders.map(basename);
    } catch {
      continue;
    }

    for (const month of sortMonthDirs(folders)) {
      const found = layoutFromFilenames(await namesIn(`${root}/${month}`));
      if (found) return found;
    }
  }

  return null;
}

/**
 * Decide how a new timeline file should be named.
 *
 * Precedence: the plugin setting, then config.yaml, then the names the
 * knowledge base already uses, then the Python default.
 *
 * The third step is why this function exists. config.yaml states the intent,
 * but the plugin cannot always read it -- on a phone the file may not have been
 * synced, and a mis-detected base folder points the read at the wrong place
 * entirely. Falling straight through to the default in those cases writes
 * "20.md" into a knowledge base whose every other file is "2026-08-20.md",
 * which splits the day across two files and hides the entry from Obsidian's
 * Calendar plugin, with nothing on screen to say why.
 *
 * @param parsed Already-parsed config.yaml, so a caller that has read it does
 *               not read it twice. Omit it to have this function read the file.
 */
export async function resolveFilenameLayout(
  adapter: DataAdapter,
  basePrefix: string,
  when: Date = new Date(),
  setting: FilenameLayoutSetting = "auto",
  parsed?: unknown
): Promise<LayoutResolution> {
  if (setting === "day" || setting === "date") {
    return { layout: setting, source: "setting" };
  }

  const config = parsed === undefined ? await readParsedConfig(adapter, basePrefix) : parsed;
  const stated = configuredFilenameLayout(config);
  if (stated) return { layout: stated, source: "config" };

  const inferred = await inferFilenameLayout(adapter, basePrefix, when);
  if (inferred) return { layout: inferred, source: "files" };

  return { layout: DEFAULT_FILENAME_LAYOUT, source: "default" };
}

/**
 * Append an entry to today's timeline file, creating it when needed.
 *
 * Appends to whichever file already holds this date -- in any of the four
 * supported layouts -- and only falls back to the configured layout when none
 * exists. Writing the configured name unconditionally would strand entries in a
 * second file whenever the knowledge base predates the current setting.
 *
 * The name a *new* file gets comes from resolveFilenameLayout rather than from
 * config.yaml alone, so a config the plugin cannot read no longer strands the
 * entry in a differently-named file.
 *
 * @param adapter    Vault adapter (raw filesystem view, dot-folders included)
 * @param basePrefix Vault-relative knowledge base prefix ("" = vault root)
 * @param message    Entry text; newlines are collapsed to keep one line per entry
 * @param options    Tags, timestamp, and the filename layout setting
 */
export async function recordDirect(
  adapter: DataAdapter,
  basePrefix: string,
  message: string,
  options: RecordOptions = {}
): Promise<RecordResult> {
  const { tags = [], when = new Date(), layoutSetting = "auto" } = options;

  const text = sanitizeMessage(message);
  if (!text) throw new Error("Cannot record an empty message.");

  const parsed = await readParsedConfig(adapter, basePrefix);
  const config = parsed === null ? { ...DEFAULT_TIMELINE_CONFIG } : timelineConfigFrom(parsed);
  const layout = await resolveFilenameLayout(adapter, basePrefix, when, layoutSetting, parsed);

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
    path = `${dir}/${filenameFor(when, layout.layout)}`;
    if (!(await adapter.exists(dir))) {
      await adapter.mkdir(dir);
    }
  }

  const entry = formatEntry(when, text, tags, config.tagFormat);
  const body = created
    ? newFileBody(when, entry)
    : appendEntry(await adapter.read(path), entry);

  await adapter.write(path, body);

  return { path, entry, created, layout };
}
