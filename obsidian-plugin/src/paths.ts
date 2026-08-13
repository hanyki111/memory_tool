/**
 * Vault-relative path construction for the configurable base folder.
 *
 * The knowledge base folder is no longer always ".memory". It can carry any
 * visible name, or be the vault root itself (base "."), which is the point of
 * the feature: Obsidian hides dot-prefixed folders, so a ".memory" base is
 * invisible in the file explorer.
 */

export const DEFAULT_BASE = ".memory";
export const ROOT_BASE = ".";

/**
 * Join path segments under the base folder, as a vault-relative path.
 *
 * A root base contributes no prefix, so "modules/x.md" rather than
 * "./modules/x.md" -- Obsidian's vault API expects no leading "./".
 */
export function underBase(baseName: string, ...segments: string[]): string {
  const parts = baseName === ROOT_BASE ? segments : [baseName, ...segments];
  return parts.filter((p) => p.length > 0).join("/");
}

/**
 * Candidate vault paths for a module, following the [Folder]/[Folder].md
 * convention with a flat [Folder].md fallback.
 */
export function moduleCandidatePaths(baseName: string, moduleName: string): string[] {
  const basename = moduleName.split("/").pop() || moduleName;
  return [
    underBase(baseName, "modules", moduleName, `${basename}.md`),
    underBase(baseName, "modules", `${moduleName}.md`),
  ];
}
