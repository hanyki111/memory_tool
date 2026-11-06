// Ordering rules for the timeline screen, kept apart from drawing so that
// `node --test` can check them. In the webview this sets window.TimelineLogic.

(function (root) {
  "use strict";

  const ENTRY = /^- (\d{1,2}:\d{2})\s*\|\s*(.+)$/;

  /**
   * A day's lines, newest entry first.
   *
   * Each entry keeps the hand-written lines that follow it, so a note stays
   * under the entry it was written about. Lines before the first entry stay on
   * top.
   *
   * Returns items of { kind: "entry", entry } or { kind: "note", text }.
   */
  function dayItems(day) {
    const entries = day.entries.slice();
    const head = [];
    const units = [];

    for (const line of day.content.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || /^#\s/.test(trimmed)) continue;

      if (ENTRY.test(trimmed) && entries.length) {
        units.push([{ kind: "entry", entry: entries.shift() }]);
      } else if (units.length) {
        units[units.length - 1].push({ kind: "note", text: trimmed });
      } else {
        head.push({ kind: "note", text: trimmed });
      }
    }

    // Entries the file walk did not meet (should not happen) still show.
    for (const entry of entries) units.push([{ kind: "entry", entry }]);

    return head.concat(...units.reverse());
  }

  /**
   * Search hits in two groups: timeline entries, newest first, then documents
   * in the order the search gave. Each item keeps its index in `results`,
   * which is what the extension is told when one is opened.
   */
  function groupHits(results) {
    const timeline = [];
    const documents = [];
    results.forEach((hit, index) => {
      (hit.kind === "timeline" && hit.entry ? timeline : documents).push({ hit, index });
    });

    const when = (item) => `${item.hit.entry.date} ${item.hit.entry.time.padStart(5, "0")}`;
    timeline.sort((a, b) => (when(a) < when(b) ? 1 : when(a) > when(b) ? -1 : a.index - b.index));

    return { timeline, documents };
  }

  const api = { dayItems, groupHits };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.TimelineLogic = api;
  }
})(typeof self !== "undefined" ? self : this);
