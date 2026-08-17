/**
 * Filesystem-only replacements for the CLI's discovery commands.
 *
 * On mobile there is no Python, so `mbase show` and `mmodule list` cannot run.
 * Both answer questions the vault can answer by itself — where the knowledge
 * base is, and which modules exist — so the plugin does not need to be crippled
 * there, only to stop shelling out.
 *
 * Module detection mirrors `ModuleManager.discover_all_modules`; the mirrored
 * rules are marked so they can be re-checked when that changes.
 */

// Type-only so this module stays importable outside Obsidian (node --test).
import type { DataAdapter } from "obsidian";
import { underBase } from "./paths.ts";

/** Folders a knowledge base is conventionally found in, most specific first. */
export const BASE_CANDIDATES = ["", ".memory", "memory"];

/** A base folder must contain both of these to be recognized. */
const BASE_MARKERS = ["timeline", "modules"];

/** Filenames that mark a legacy multi-file module by their presence. */
const LEGACY_FILES = new Set([
  "module.md",
  "current.md",
  "decisions.md",
  "dependencies.md",
  "interface.md",
]);

/** Minimal slice of DataAdapter used here, so tests can supply a fake. */
export interface ScanAdapter {
  exists(path: string): Promise<boolean>;
  list(path: string): Promise<{ files: string[]; folders: string[] }>;
}

/**
 * Find the knowledge base by looking for its marker folders.
 *
 * Used when the CLI cannot be asked. Returns the first candidate holding both
 * `timeline/` and `modules/`, or null when none does — a null is reported to
 * the user rather than guessed at, because writing capture into the wrong
 * folder produces entries that no command will ever find.
 */
export async function probeBasePrefix(
  adapter: ScanAdapter,
  candidates: string[] = BASE_CANDIDATES
): Promise<string | null> {
  for (const prefix of candidates) {
    const checks = await Promise.all(
      BASE_MARKERS.map((marker) => adapter.exists(underBase(prefix, marker)))
    );
    if (checks.every(Boolean)) return prefix;
  }
  return null;
}

/** Last path segment of a vault path. */
function basename(path: string): string {
  return path.split("/").filter(Boolean).pop() ?? path;
}

/** Strip a trailing ".md". */
function stem(name: string): string {
  return name.endsWith(".md") ? name.slice(0, -3) : name;
}

/**
 * Files the CLI ignores when discovering modules.
 * Mirrors the `_`-prefix / all-uppercase / MIGRATION-SUMMARY skips.
 */
function isIgnoredFile(name: string): boolean {
  if (name.startsWith("_")) return true;
  if (name === "MIGRATION-SUMMARY.md") return true;
  // All-uppercase stems are meta/index documents, not modules (PLAN.md etc).
  const base = stem(name);
  return base === base.toUpperCase() && /[A-Z]/.test(base);
}

/**
 * List every module under the knowledge base.
 *
 * Mirrors `ModuleManager.discover_all_modules`, including its three layouts:
 *   1. `A/B/B.md`      -- folder-encapsulated single file
 *   2. `A/B.md`        -- flat single file
 *   3. `A/B/module.md` -- legacy multi-file, represented by its folder
 *
 * @returns Module paths relative to `modules/`, sorted, forward-slashed.
 */
export async function listModules(
  adapter: ScanAdapter,
  basePrefix: string
): Promise<string[]> {
  const root = underBase(basePrefix, "modules");
  if (!(await adapter.exists(root))) return [];

  const found = new Set<string>();

  const walk = async (dir: string, relative: string): Promise<void> => {
    let listing;
    try {
      listing = await adapter.list(dir);
    } catch {
      return;
    }

    for (const filePath of listing.files) {
      const name = basename(filePath);
      if (!name.endsWith(".md") || isIgnoredFile(name)) continue;

      if (LEGACY_FILES.has(name)) {
        // Layout 3: the folder itself is the module.
        if (relative) found.add(relative);
        continue;
      }

      if (relative && stem(name) === basename(relative)) {
        // Layout 1: A/B/B.md -- the folder is the module, not the file.
        found.add(relative);
        continue;
      }

      // Layout 2: a flat single-file module.
      const flat = relative ? `${relative}/${stem(name)}` : stem(name);
      found.add(flat);
    }

    for (const folderPath of listing.folders) {
      const name = basename(folderPath);
      // Archived modules are not listed, matching the CLI.
      if (name === "archive" || name.startsWith(".")) continue;
      await walk(folderPath, relative ? `${relative}/${name}` : name);
    }
  };

  await walk(root, "");

  return [...found].sort();
}

/** Adapt Obsidian's DataAdapter to the narrow interface used here. */
export function asScanAdapter(adapter: DataAdapter): ScanAdapter {
  return {
    exists: (path: string) => adapter.exists(path),
    list: (path: string) => adapter.list(path),
  };
}
