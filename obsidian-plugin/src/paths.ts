/**
 * Vault-relative path construction for the knowledge base folder.
 *
 * The important subtlety: memory_tool reports the base folder relative to the
 * *project root*, but Obsidian's vault API needs paths relative to the *vault
 * root*. Those are not the same thing.
 *
 *   vault = project root, base = .memory   ->  prefix ".memory"
 *   vault = the .memory folder itself      ->  prefix ""      <- common setup
 *   vault = project root, base = memory    ->  prefix "memory"
 *   vault = project root, base = "."       ->  prefix ""
 *
 * Using the base *name* as the prefix breaks the second case: the vault root is
 * already .memory, so ".memory/modules/x.md" resolves to .memory/.memory/... and
 * nothing is found. Everything here works from absolute paths instead.
 */

export const DEFAULT_BASE = ".memory";
export const ROOT_BASE = ".";

/** Normalize a filesystem path for comparison (separators, trailing slash). */
function normalize(p: string): string {
  return p.replace(/\\/g, "/").replace(/\/+$/, "");
}

/**
 * Windows paths are case-insensitive, and Obsidian and Python can disagree on
 * drive-letter case ("E:\..." vs "e:\..."), so compare case-insensitively.
 */
function sameHost(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

/**
 * Work out the vault-relative prefix for the knowledge base folder.
 *
 * @param vaultRoot Absolute path of the vault root
 * @param absoluteBase Absolute path of the base folder, from `mbase show --json`
 * @returns The prefix ("" when the vault root *is* the base folder), or null
 *          when the base lies outside the vault and Obsidian cannot open it.
 */
export function vaultRelativeBase(
  vaultRoot: string,
  absoluteBase: string
): string | null {
  const root = normalize(vaultRoot);
  const base = normalize(absoluteBase);

  if (!root || !base) return null;
  if (sameHost(root, base)) return "";

  const withSep = root + "/";
  if (base.toLowerCase().startsWith(withSep.toLowerCase())) {
    return base.slice(withSep.length);
  }

  // The base is outside the vault (or the vault is inside the base). Obsidian
  // cannot address either case with a relative path.
  return null;
}

/**
 * Turn a user-entered override into a prefix.
 * "." and "./" mean the vault root, so they become an empty prefix.
 */
export function normalizePrefix(value: string): string {
  const trimmed = value.trim().replace(/\\/g, "/").replace(/^\.\//, "").replace(/\/+$/, "");
  if (trimmed === "" || trimmed === ".") return "";
  return trimmed;
}

/** Join path segments under the base folder, as a vault-relative path. */
export function underBase(basePrefix: string, ...segments: string[]): string {
  const parts = basePrefix ? [basePrefix, ...segments] : segments;
  return parts.filter((p) => p.length > 0).join("/");
}

/**
 * Candidate vault paths for a module.
 *
 * Two layouts exist in the wild and both are supported, in this order:
 *   1. modules/A/B/B.md   -- [Folder]/[Folder].md encapsulation
 *   2. modules/A/B.md     -- the .md as a sibling of its subfolder
 *
 * `mmodule list` prints nested names with the host separator, so on Windows they
 * arrive as "A\B". Obsidian vault paths are always forward-slashed, so the name
 * is normalized before use -- otherwise every nested module fails to open.
 */
export function moduleCandidatePaths(basePrefix: string, moduleName: string): string[] {
  const name = moduleName
    .replace(/\\/g, "/")
    .replace(/\/{2,}/g, "/")
    .replace(/^\/+|\/+$/g, "");
  const basename = name.split("/").pop() || name;
  return [
    underBase(basePrefix, "modules", name, `${basename}.md`),
    underBase(basePrefix, "modules", `${name}.md`),
  ];
}

/**
 * The part of a vault path that sits under `<base>/modules`, or null.
 *
 * Shared by the two inverse lookups below: both need to know whether a path is
 * inside the modules tree at all, and neither should treat the archive as one.
 */
function underModules(basePrefix: string, vaultPath: string): string | null {
  const path = normalize(vaultPath).replace(/^\/+/, "");
  const root = underBase(basePrefix, "modules");

  if (path.toLowerCase() === root.toLowerCase()) return "";

  const withSep = root + "/";
  if (!path.toLowerCase().startsWith(withSep.toLowerCase())) return null;

  const rest = path.slice(withSep.length);
  // Archived modules are not editable in place; `mmodule unarchive` moves them
  // back first, so offering to create or grow one here would mislead.
  if (rest.toLowerCase() === "archive" || rest.toLowerCase().startsWith("archive/")) {
    return null;
  }

  return rest;
}

/**
 * Module name for a document, or null when the file is not a module.
 *
 * The inverse of {@link moduleCandidatePaths}, and it has to undo both layouts:
 *
 *   modules/A/B/B.md  ->  "A/B"   (encapsulated: stem repeats its folder)
 *   modules/A/B.md    ->  "A/B"   (flat)
 *
 * @param basePrefix Vault-relative base prefix ("" = the vault root)
 * @param filePath Vault-relative path of the document
 */
export function moduleNameFromPath(
  basePrefix: string,
  filePath: string
): string | null {
  const rest = underModules(basePrefix, filePath);
  if (!rest || !rest.toLowerCase().endsWith(".md")) return null;

  const segments = rest.slice(0, -3).split("/").filter((s) => s.length > 0);
  if (segments.length === 0) return null;

  const stem = segments[segments.length - 1];
  const parent = segments.length > 1 ? segments[segments.length - 2] : null;

  // "A/B/B.md" names the module "A/B"; the repeated leaf is the file, not a level.
  if (parent !== null && parent === stem) {
    return segments.slice(0, -1).join("/");
  }

  return segments.join("/");
}

/**
 * Module-name prefix for a folder, for pre-filling the create dialog.
 *
 * @param basePrefix Vault-relative base prefix ("" = the vault root)
 * @param folderPath Vault-relative path of the folder
 * @returns "" for the modules folder itself, "A/B" for a folder inside it, or
 *          null when the folder is outside the modules tree. Modules only ever
 *          live under `<base>/modules`, so anywhere else has no answer.
 */
export function modulePrefixFromFolder(
  basePrefix: string,
  folderPath: string
): string | null {
  return underModules(basePrefix, folderPath);
}

/** Human-readable description of a prefix, for notices and settings. */
export function describePrefix(basePrefix: string): string {
  return basePrefix === "" ? "the vault root" : `${basePrefix}/`;
}
