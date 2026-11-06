import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

import { escapeHtml, newNonce, page } from "../src/html.ts";
import { fill, stringsFor } from "../src/strings.ts";

const here = path.dirname(fileURLToPath(import.meta.url));

test("the page allows only its own script and style", () => {
  const html = page({
    cspSource: "vscode-resource:",
    scriptUri: "vscode-resource:/timeline.js",
    logicUri: "vscode-resource:/logic.js",
    styleUri: "vscode-resource:/timeline.css",
    nonce: "abc",
    strings: stringsFor("en"),
    inEditor: false,
    language: "en",
  });

  assert.match(html, /default-src 'none'/);
  assert.match(html, /script-src 'nonce-abc'/);
  assert.doesNotMatch(html, /unsafe-inline/);
  assert.match(html, /<script nonce="abc" src="vscode-resource:\/timeline.js">/);
});

test("the strings go in escaped", () => {
  const strings = { ...stringsFor("en"), record: `"><script>alert(1)</script>` };
  const html = page({ cspSource: "x", scriptUri: "s", logicUri: "l", styleUri: "c", nonce: "n", strings, inEditor: true, language: "en" });

  assert.doesNotMatch(html, /<script>alert/);
  const config = /data-config="([^"]*)"/.exec(html)[1];
  const decoded = config.replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&#39;/g, "'").replace(/&amp;/g, "&");
  assert.equal(JSON.parse(decoded).strings.record, strings.record);
});

test("escapeHtml", () => {
  assert.equal(escapeHtml(`<a href="x">'&'</a>`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
});

test("nonces differ", () => {
  assert.notEqual(newNonce(), newNonce());
  assert.match(newNonce(), /^[A-Za-z0-9]{32}$/);
});

test("Korean for a Korean display language, English otherwise", () => {
  assert.equal(stringsFor("ko").record, "기록");
  assert.equal(stringsFor("ko-KR").record, "기록");
  assert.equal(stringsFor("en-US").record, "Record");
  assert.equal(stringsFor("ja").record, "Record");
});

test("both languages have the same words", () => {
  assert.deepEqual(Object.keys(stringsFor("ko")).sort(), Object.keys(stringsFor("en")).sort());
});

test("fill", () => {
  assert.equal(fill("{a} and {b} and {c}", { a: 1, b: "x" }), "1 and x and {c}");
});

test("the screen script parses", () => {
  execFileSync(process.execPath, ["--check", path.join(here, "..", "media", "timeline.js")]);
});
