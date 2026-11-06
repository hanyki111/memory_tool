// The timeline screen. It draws what the extension sends and posts back what
// the person asks for; all state lives in the extension.
//
// Text from the knowledge base is only ever set with textContent.

(function () {
  "use strict";

  const vscode = acquireVsCodeApi();
  const config = JSON.parse(document.body.dataset.config);
  const t = config.strings;
  const ENTRY = /^- (\d{1,2}:\d{2})\s*\|\s*(.+)$/;

  const fill = (template, values) =>
    template.replace(/\{(\w+)\}/g, (whole, name) => (name in values ? String(values[name]) : whole));

  // ---- elements -----------------------------------------------------------

  function el(tag, attributes, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attributes || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children) {
      if (child) node.append(child);
    }
    return node;
  }

  const app = document.getElementById("app");

  const recordInput = el("input", {
    type: "text",
    class: "record-input",
    placeholder: t.recordPlaceholder,
    "aria-label": t.recordPlaceholder,
    onkeydown: (event) => {
      if (event.key === "Enter" && !event.isComposing) {
        event.preventDefault();
        record();
      }
    },
  });
  const recordButton = el("button", { class: "primary", text: t.record, onclick: () => record() });

  const searchInput = el("input", {
    type: "search",
    placeholder: t.searchPlaceholder,
    "aria-label": t.searchPlaceholder,
    onkeydown: (event) => {
      if (event.key === "Enter" && !event.isComposing) {
        event.preventDefault();
        search(false);
      } else if (event.key === "Escape") {
        clearSearch();
      }
    },
  });
  const searchButton = el("button", { text: t.search, onclick: () => search(false) });
  const semanticButton = el("button", { text: t.semantic, title: t.semanticTitle, onclick: () => search(true) });

  const fromInput = el("input", { type: "date", "aria-label": t.from });
  const toInput = el("input", { type: "date", "aria-label": t.to });

  const reviewButton = el("button", { onclick: () => vscode.postMessage({ type: "review" }) });
  const widenButton = config.inEditor
    ? null
    : el("button", { text: t.widen, onclick: () => vscode.postMessage({ type: "widen" }) });

  const period = el(
    "details",
    { class: "period" },
    el("summary", { text: t.period }),
    el(
      "div",
      { class: "row wrap" },
      el("label", {}, el("span", { text: t.from }), fromInput),
      el("label", {}, el("span", { text: t.to }), toInput),
      el("button", { text: t.go, onclick: () => goTo(fromInput.value, toInput.value) }),
      el("button", { text: t.thisWeek, onclick: () => quick("thisWeek") }),
      el("button", { text: t.lastWeek, onclick: () => quick("lastWeek") }),
      el("button", { text: t.thisMonth, onclick: () => quick("thisMonth") }),
      el("button", { text: t.latest, onclick: () => vscode.postMessage({ type: "latest" }) })
    )
  );

  const banner = el("div", { class: "banner", role: "alert", hidden: true });
  const status = el("div", { class: "status", "aria-live": "polite" });
  const list = el("div", { class: "list" });
  const sentinel = el("div", { class: "sentinel" });

  app.append(
    el(
      "header",
      {},
      el("div", { class: "row" }, recordInput, recordButton),
      el("div", { class: "row" }, searchInput, searchButton, semanticButton),
      period,
      el("div", { class: "row tools" }, status, reviewButton, widenButton)
    ),
    banner,
    list,
    sentinel
  );

  // A wide screen shows the period controls; a narrow one folds them away.
  const wide = window.matchMedia("(min-width: 560px)");
  const fitPeriod = () => (period.open = wide.matches);
  wide.addEventListener("change", fitPeriod);
  fitPeriod();

  // ---- actions ------------------------------------------------------------

  function record() {
    const text = recordInput.value.trim();
    if (!text || model.busy === "recording") return;
    vscode.postMessage({ type: "record", text });
  }

  function search(semantic) {
    const query = searchInput.value.trim();
    if (!query) return;
    rememberScroll();
    vscode.postMessage({ type: "search", query, semantic });
  }

  function clearSearch() {
    searchInput.value = "";
    if (model.search) vscode.postMessage({ type: "clearSearch" });
  }

  function goTo(from, to) {
    if (!from && !to) return;
    vscode.postMessage({ type: "jump", from: from || to, to: to || from });
  }

  function quick(which) {
    vscode.postMessage({ type: "quick", which });
  }

  // ---- drawing ------------------------------------------------------------

  let model = { status: "loading", days: [], search: null, busy: "loading" };
  let timelineScroll = 0;
  let lastHighlight = null;

  function rememberScroll() {
    if (!model.search) timelineScroll = document.scrollingElement.scrollTop;
  }

  function showBanner(message) {
    banner.textContent = message || "";
    banner.hidden = !message;
  }

  function tagged(text, tags) {
    // Mark the tags inside the text as written, without changing the text.
    const span = el("span", { class: "text" });
    if (!tags || !tags.length) {
      span.textContent = text;
      return span;
    }
    const names = tags.map((tag) => tag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
    const pattern = new RegExp(`(\\[(?:${names})\\]|#(?:${names})(?![\\w가-힣-]))`, "g");
    let last = 0;
    for (const match of text.matchAll(pattern)) {
      if (match.index > last) span.append(text.slice(last, match.index));
      span.append(el("span", { class: "tag", text: match[0] }));
      last = match.index + match[0].length;
    }
    span.append(text.slice(last));
    return span;
  }

  function entryRow(entry, key) {
    return el(
      "div",
      { class: "entry" + (key === model.highlight ? " highlight" : ""), "data-key": key },
      el("span", { class: "time", text: entry.time }),
      tagged(entry.text, entry.tags)
    );
  }

  function dayBlock(day) {
    const block = el(
      "section",
      { class: "day" },
      el(
        "h2",
        {},
        el("button", {
          class: "link",
          text: day.date,
          title: t.openFile,
          onclick: () => vscode.postMessage({ type: "openFile", path: day.path, line: 1 }),
        })
      )
    );

    // Walk the file so hand-written lines keep their place among the entries.
    const entries = day.entries.slice();
    for (const line of day.content.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || /^#\s/.test(trimmed)) continue;

      const match = ENTRY.exec(trimmed);
      if (match && entries.length) {
        const entry = entries.shift();
        block.append(entryRow(entry, `${day.date} ${entry.time} ${entry.text}`));
      } else {
        block.append(el("div", { class: "note", text: trimmed }));
      }
    }
    return block;
  }

  function hitRow(hit, index) {
    const where =
      hit.kind === "timeline" && hit.entry
        ? `${hit.entry.date} ${hit.entry.time}`
        : `${hit.path.split(/[\\/]/).slice(-2).join("/")}:${hit.line}`;
    return el(
      "button",
      { class: "hit", onclick: () => vscode.postMessage({ type: "openHit", index }) },
      el("span", { class: "where", text: where }),
      hit.entry ? tagged(hit.entry.text, hit.entry.tags) : el("span", { class: "text", text: hit.text.trim() })
    );
  }

  function render() {
    list.replaceChildren();
    sentinel.replaceChildren();
    showBanner(model.error);

    if (model.status === "nofolder" || model.status === "nobase") {
      const empty = el("div", { class: "empty" });
      if (model.status === "nofolder") {
        empty.append(el("p", { text: t.noFolder }));
      } else {
        empty.append(el("p", { class: "strong", text: t.noBaseTitle }), el("p", { text: t.noBaseBody }));
      }
      list.append(empty);
      status.textContent = "";
      reviewButton.hidden = true;
      return;
    }

    reviewButton.hidden = false;
    if (model.loaded) {
      reviewButton.textContent = fill(t.review, { date: model.loaded.from });
      reviewButton.title = fill(t.reviewTitle, { date: model.loaded.from });
    }

    const busyText = { loading: t.loading, searching: t.searching, recording: t.recording }[model.busy];
    recordButton.disabled = model.busy === "recording";

    if (model.search) {
      const { query, results } = model.search;
      status.textContent = busyText || fill(results.length ? t.resultsFor : t.noResults, { query, count: results.length });
      list.append(el("button", { class: "link back", text: `← ${t.clearSearch}`, onclick: clearSearch }));
      results.forEach((hit, index) => list.append(hitRow(hit, index)));
      return;
    }

    status.textContent = busyText || (model.loaded ? fill(t.showing, model.loaded) : "");
    for (const day of model.days) list.append(dayBlock(day));
    if (!model.days.length && !model.busy) list.append(el("p", { class: "empty", text: t.noEntries }));

    sentinel.append(el("p", { class: "muted", text: model.hasOlder ? t.loadingOlder : t.noOlder }));
  }

  function afterRender(previous) {
    if (model.search) {
      if (!previous.search) document.scrollingElement.scrollTop = 0;
      return;
    }
    if (previous.search) {
      document.scrollingElement.scrollTop = timelineScroll;
    }
    if (model.highlight && model.highlight !== lastHighlight) {
      const target = list.querySelector(`[data-key="${CSS.escape(model.highlight)}"]`);
      if (target) target.scrollIntoView({ block: "center" });
    }
    lastHighlight = model.highlight;
    maybeLoadOlder();
  }

  // ---- loading older days -----------------------------------------------

  function maybeLoadOlder() {
    if (model.search || model.busy || !model.hasOlder) return;
    const rect = sentinel.getBoundingClientRect();
    if (rect.top < window.innerHeight + 200) {
      vscode.postMessage({ type: "older" });
    }
  }

  new IntersectionObserver(() => maybeLoadOlder(), { rootMargin: "200px" }).observe(sentinel);

  // ---- messages -----------------------------------------------------------

  window.addEventListener("message", (event) => {
    const message = event.data;
    if (message.type === "render") {
      const previous = model;
      model = message.model;
      if (model.loaded) {
        fromInput.value = model.loaded.from;
        toInput.value = model.loaded.to;
      }
      render();
      afterRender(previous);
    } else if (message.type === "recorded") {
      recordInput.value = "";
      recordInput.focus();
    } else if (message.type === "focusRecord") {
      recordInput.focus();
    }
  });

  vscode.postMessage({ type: "ready" });
})();
