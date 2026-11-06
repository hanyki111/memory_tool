/** Facts about a knowledge base read straight from its folders. No VS Code API. */

import * as fs from "node:fs";
import * as path from "node:path";

const MONTH = /^(\d{4})-(\d{2})$/;

/**
 * The first day of the earliest month that has a timeline folder, or null.
 *
 * Scrolling stops there. Both layouts count: timeline/daily/YYYY-MM and the
 * older timeline/YYYY-MM.
 */
export function earliestDate(base: string): string | null {
  const timeline = path.join(base, "timeline");
  const months: string[] = [];

  for (const folder of [path.join(timeline, "daily"), timeline]) {
    let names: string[];
    try {
      names = fs.readdirSync(folder);
    } catch {
      continue;
    }
    for (const name of names) {
      if (MONTH.test(name)) {
        months.push(name);
      }
    }
  }

  if (!months.length) {
    return null;
  }
  months.sort();
  return `${months[0]}-01`;
}
