import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { dayItems, groupHits } = require("../media/logic.js");

const entry = (time, text) => ({ date: "2026-11-06", time, text, tags: [] });

describe("a day's lines", () => {
  test("newest entry first", () => {
    const day = {
      entries: [entry("09:00", "first"), entry("13:00", "second"), entry("21:00", "third")],
      content: "# 2026-11-06 Timeline\n- 09:00 | first\n- 13:00 | second\n- 21:00 | third\n",
    };

    assert.deepEqual(dayItems(day).map((item) => item.entry.text), ["third", "second", "first"]);
  });

  test("a hand-written line stays under the entry it follows", () => {
    const day = {
      entries: [entry("09:00", "first"), entry("13:00", "second")],
      content: "# T\nintro note\n- 09:00 | first\n  detail of first\n- 13:00 | second\n",
    };

    assert.deepEqual(
      dayItems(day).map((item) => (item.kind === "entry" ? item.entry.text : `note: ${item.text}`)),
      ["note: intro note", "second", "first", "note: detail of first"]
    );
  });
});

describe("search hits", () => {
  const timelineHit = (date, time, text) => ({ kind: "timeline", path: `/t/${date}.md`, entry: { date, time, text, tags: [] } });
  const documentHit = (name) => ({ kind: "module", path: `/m/${name}.md`, line: 1, text: name });

  test("timeline entries come first, newest first; documents keep their order", () => {
    const results = [
      documentHit("b"),
      timelineHit("2025-11-15", "9:05", "old"),
      documentHit("a"),
      timelineHit("2026-11-06", "21:04", "new"),
      timelineHit("2026-11-06", "10:00", "morning"),
    ];

    const { timeline, documents } = groupHits(results);

    assert.deepEqual(timeline.map((item) => item.hit.entry.text), ["new", "morning", "old"]);
    assert.deepEqual(documents.map((item) => item.hit.text), ["b", "a"]);
    assert.deepEqual(timeline.map((item) => item.index), [3, 4, 1]);
  });

  test("a timeline hit without its entry is listed with the documents", () => {
    const { timeline, documents } = groupHits([{ kind: "timeline", path: "/t/x.md", line: 2, text: "x" }]);
    assert.equal(timeline.length, 0);
    assert.equal(documents.length, 1);
  });
});
