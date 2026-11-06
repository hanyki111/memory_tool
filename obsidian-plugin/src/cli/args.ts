/**
 * Command lines for the memory_tool CLI, as argument arrays.
 *
 * The arrays go to execFile, never through a shell, so quotes, %, $ and every
 * other character in a message reach the CLI as written. "--" ends the options
 * before text the person wrote, so a message starting with "-" stays a message.
 *
 * No Obsidian API here, so `node --test` can check it.
 */

/**
 * Split the Python setting into a program and its own arguments.
 *
 * The setting used to go through a shell, so values such as `py -3` and
 * `"C:\Program Files\Python313\python.exe"` worked; they still do. A path that
 * exists as written is used whole, spaces and all.
 */
export function commandParts(setting: string, exists: (path: string) => boolean = () => false): string[] {
  const value = (setting || "").trim() || "python";

  const quoted = /^"([^"]+)"\s*(.*)$/.exec(value);
  if (quoted) {
    return [quoted[1], ...splitWords(quoted[2])];
  }
  if (exists(value)) {
    return [value];
  }
  return splitWords(value);
}

function splitWords(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

/** A timeline entry is one line; line breaks in the text become spaces. */
export function oneLine(text: string): string {
  return text.replace(/[\r\n]+/g, " ").trim();
}

export function recordArgs(message: string): string[] {
  return ["record", "--", oneLine(message)];
}

export function createModuleArgs(name: string, description = "", tags = "", docType = ""): string[] {
  const args = ["module", "create"];
  if (description) args.push("--desc", oneLine(description));
  if (tags) args.push("--tags", oneLine(tags));
  if (docType) args.push("--type", oneLine(docType));
  args.push("--", name);
  return args;
}

export function askArgs(question: string, opts: { simple?: boolean; provider?: string } = {}): string[] {
  const args = ["ask", "--json"];
  if (opts.simple) args.push("--simple");
  if (opts.provider) args.push("--provider", oneLine(opts.provider));
  args.push("--", oneLine(question));
  return args;
}
