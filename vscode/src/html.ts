/** The webview page. The screen itself is media/timeline.js and timeline.css. */

import type { Strings } from "./strings.ts";

export interface PageParts {
  /** webview.cspSource */
  cspSource: string;
  scriptUri: string;
  /** media/logic.js, which the screen script uses */
  logicUri: string;
  styleUri: string;
  nonce: string;
  strings: Strings;
  /** True in an editor tab, where "Open wide" makes no sense */
  inEditor: boolean;
  language: string;
}

export function newNonce(): string {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let nonce = "";
  for (let i = 0; i < 32; i++) {
    nonce += letters.charAt(Math.floor(Math.random() * letters.length));
  }
  return nonce;
}

/** Escape text for an HTML attribute or element. */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function page(parts: PageParts): string {
  const csp = [
    "default-src 'none'",
    `style-src ${parts.cspSource}`,
    `script-src 'nonce-${parts.nonce}'`,
    `img-src ${parts.cspSource}`,
  ].join("; ");

  // The strings go in as JSON in a data attribute rather than inline script, so
  // the CSP needs no 'unsafe-inline'.
  const config = escapeHtml(JSON.stringify({ strings: parts.strings, inEditor: parts.inEditor }));

  return `<!DOCTYPE html>
<html lang="${escapeHtml(parts.language)}">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="${escapeHtml(parts.styleUri)}">
<title>Timeline</title>
</head>
<body data-config="${config}">
<div id="app"></div>
<script nonce="${parts.nonce}" src="${escapeHtml(parts.logicUri)}"></script>
<script nonce="${parts.nonce}" src="${escapeHtml(parts.scriptUri)}"></script>
</body>
</html>`;
}
