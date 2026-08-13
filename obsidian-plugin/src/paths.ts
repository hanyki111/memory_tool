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

/** Human-readable description of a prefix, for notices and settings. */
export function describePrefix(basePrefix: string): string {
  return basePrefix === "" ? "the vault root" : `${basePrefix}/`;
}
