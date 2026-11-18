// The timeline screen. It draws what the extension sends and posts back what
// the person asks for; all state lives in the extension.
//
// Text from the knowledge base is only ever set with textContent.

(function () {
  "use strict";

  const vscode = acquireVsCodeApi();
  const config = JSON.parse(document.body.dataset.config);
  const t = config.strings;
  const { dayItems, groupHits } = window.TimelineLogic;

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

  // Enter records; Shift+Enter starts a new line, which the CLI writes as a
  // later line of the same entry. A composing Enter is ignored: with a Korean
  // IME it carries a syllable the box has not committed yet.
  const recordInput = el("textarea", {
    class: "record-input",
    rows: "1",
    placeholder: t.recordPlaceholder,
    "aria-label": t.recordPlaceholder,
    onkeydown: (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        record();
      }
    },
    oninput: () => fitRecordInput(),
  });

  // The box grows with what is typed, up to a limit set in the stylesheet.
  function fitRecordInput() {
    recordInput.style.height = "auto";
    recordInput.style.height = `${recordInput.scrollHeight + recordInput.offsetHeight - recordInput.clientHeight}px`;
  }
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

  const reviewButton = el("button", {
    text: t.review,
    title: t.reviewTitle,
    onclick: () => vscode.postMessage({ type: "review" }),
  });
  const reviewFromButton = el("button", { onclick: () => vscode.postMessage({ type: "reviewFrom" }) });
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
      el("button", { text: t.latest, onclick: () => vscode.postMessage({ type: "latest" }) }),
      reviewFromButton
    )
  );

  const banner = el("div", { class: "banner", role: "alert", hidden: true });
  const status = el("div", { class: "status", "aria-live": "polite" });
  const list = el("div", { class: "list" });
  const sentinel = el("div", { class: "sentinel" });
  // The timeline scrolls on its own, between the controls above and the plan below.
  const timeline = el("main", { class: "timeline" }, list, sentinel);

  // ---- today's plan ---------------------------------------------------------

  const layout = (() => {
    try {
      return vscode.getState() || {};
    } catch {
      return {};
    }
  })();
  let planOpen = layout.planOpen !== false;
  let planHeight = Number(layout.planHeight) || 220;

  function saveLayout() {
    try {
      vscode.setState({ ...(vscode.getState() || {}), planOpen, planHeight });
    } catch {
      // The layout is a convenience; losing it is fine.
    }
  }

  const planProgress = el("span", { class: "plan-progress" });
  const planToggle = el(
    "button",
    { class: "plan-toggle", title: t.planToggle, onclick: () => setPlanOpen(!planOpen) },
    el("span", { class: "chevron", "aria-hidden": "true" }),
    el("span", { text: t.planTitle }),
    planProgress
  );
  const planCarryButton = el("button", {
    class: "link",
    text: t.planCarryover,
    onclick: () => vscode.postMessage({ type: "planCarryover" }),
  });
  const planOpenButton = el("button", {
    class: "link",
    text: t.planOpen,
    onclick: () => vscode.postMessage({ type: "planOpen" }),
  });
  const planMessage = el("p", { class: "plan-message muted", hidden: true });
  const planError = el("div", { class: "banner", role: "alert", hidden: true });
  const planList = el("ul", { class: "plan-tasks" });
  const planInput = el("input", {
    type: "text",
    placeholder: t.planAddPlaceholder,
    "aria-label": t.planAddPlaceholder,
    onkeydown: (event) => {
      if (event.key === "Enter" && !event.isComposing) {
        event.preventDefault();
        addTask();
      }
    },
  });
  const planAddButton = el("button", { text: t.planAdd, onclick: () => addTask() });
  const planAddRow = el("div", { class: "row" }, planInput, planAddButton);
  const planRecurringText = el("div", { class: "plan-recurring-text" });
  const planRecurring = el("details", { class: "plan-recurring", hidden: true }, el("summary", { text: t.planRecurring }), planRecurringText);
  const planBody = el(
    "div",
    { class: "plan-body", id: "plan-body" },
    planError,
    planMessage,
    planList,
    planAddRow,
    el("div", { class: "row plan-links" }, planCarryButton, planOpenButton),
    planRecurring
  );
  planToggle.setAttribute("aria-controls", "plan-body");
  const planSection = el(
    "section",
    { class: "plan", "aria-label": t.planTitle, hidden: true },
    el("div", { class: "plan-head" }, planToggle),
    planBody
  );

  // The edge between the timeline and the plan: drag it, or use the arrow keys.
  const splitter = el("div", {
    class: "splitter",
    role: "separator",
    tabindex: "0",
    "aria-orientation": "horizontal",
    "aria-label": t.planResize,
    title: t.planResize,
  });

  const header = el(
    "header",
    {},
    el("div", { class: "row record" }, recordInput, recordButton),
    el("div", { class: "row" }, searchInput, searchButton, semanticButton),
    period,
    el("div", { class: "row tools" }, status, reviewButton, widenButton)
  );

  app.append(header, banner, timeline, splitter, planSection);

  const PLAN_MIN = 72;
  const TIMELINE_MIN = 80;

  /** The plan's height, kept between its minimum and what leaves the timeline room. */
  function clampPlan(height) {
    const room = window.innerHeight - header.offsetHeight - banner.offsetHeight - splitter.offsetHeight - TIMELINE_MIN;
    return Math.round(Math.max(PLAN_MIN, Math.min(height, Math.max(PLAN_MIN, room))));
  }

  function fitPlan() {
    planSection.classList.toggle("closed", !planOpen);
    planToggle.setAttribute("aria-expanded", String(planOpen));
    planBody.hidden = !planOpen;
    splitter.hidden = !planOpen || planSection.hidden;
    if (planOpen) {
      const height = clampPlan(planHeight);
      planSection.style.height = `${height}px`;
      splitter.setAttribute("aria-valuenow", String(height));
    } else {
      planSection.style.height = "";
    }
  }

  function setPlanOpen(open) {
    planOpen = open;
    fitPlan();
    saveLayout();
  }

  function setPlanHeight(height) {
    planHeight = clampPlan(height);
    fitPlan();
  }

  let drag = null;
  splitter.addEventListener("pointerdown", (event) => {
    drag = { y: event.clientY, height: planSection.offsetHeight };
    splitter.setPointerCapture(event.pointerId);
    splitter.classList.add("dragging");
    event.preventDefault();
  });
  splitter.addEventListener("pointermove", (event) => {
    if (drag) setPlanHeight(drag.height + (drag.y - event.clientY));
  });
  const endDrag = () => {
    if (!drag) return;
    drag = null;
    splitter.classList.remove("dragging");
    saveLayout();
  };
  splitter.addEventListener("pointerup", endDrag);
  splitter.addEventListener("pointercancel", endDrag);
  splitter.addEventListener("keydown", (event) => {
    const step = event.shiftKey ? 64 : 16;
    if (event.key === "ArrowUp") setPlanHeight(planSection.offsetHeight + step);
    else if (event.key === "ArrowDown") setPlanHeight(planSection.offsetHeight - step);
    else if (event.key === "Enter") setPlanOpen(!planOpen);
    else return;
    event.preventDefault();
    saveLayout();
  });
  window.addEventListener("resize", () => fitPlan());
  fitPlan();

  function addTask() {
    const text = planInput.value.trim();
    if (!text || model.plan?.busy) return;
    vscode.postMessage({ type: "planAdd", text });
  }

  function renderPlan() {
    const view = model.plan;
    planSection.hidden = model.status !== "ready" || !view;
    splitter.hidden = planSection.hidden || !planOpen;
    if (planSection.hidden) return;

    const plan = view.plan;
    const busy = Boolean(view.busy);
    planError.textContent = view.error || "";
    planError.hidden = !view.error;
    planList.replaceChildren();

    let message = "";
    if (view.status === "outdated") message = t.planOutdated;
    else if (!plan) message = view.error ? "" : t.planLoading;
    else if (!plan.tasks.length) message = t.planEmpty;
    planMessage.textContent = message;
    planMessage.hidden = !message;

    const usable = view.status === "ready" && Boolean(plan);
    planAddRow.hidden = !usable;
    planCarryButton.hidden = !usable;
    planOpenButton.hidden = !usable || !plan.exists;
    planInput.disabled = busy;
    planAddButton.disabled = busy;
    planCarryButton.disabled = busy;
    planProgress.textContent = plan && plan.progress.total ? `${plan.progress.done}/${plan.progress.total}` : "";

    for (const task of plan ? plan.tasks : []) {
      const box = el("input", {
        type: "checkbox",
        checked: task.done,
        disabled: busy,
        onchange: () => vscode.postMessage({ type: "planSet", line: task.line, text: task.text, done: box.checked }),
      });
      planList.append(
        el(
          "li",
          { class: "plan-task" + (task.done ? " done" : "") },
          el("label", {}, box, el("span", { class: "text", text: task.text }), task.done && task.time ? el("span", { class: "time", text: task.time }) : null)
        )
      );
    }

    planRecurring.hidden = !(plan && plan.recurring);
    planRecurringText.textContent = (plan && plan.recurring) || "";
  }

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
    if (!model.search) timelineScroll = timeline.scrollTop;
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

    // Newest entry first; an entry's later lines, and lines written by hand,
    // stay under the entry they follow, lined up with its text.
    let time = "00:00"; // lines before the first entry line up as if under one
    for (const item of dayItems(day)) {
      if (item.kind === "entry") {
        const entry = item.entry;
        time = entry.time;
        block.append(entryRow(entry, `${day.date} ${entry.time} ${entry.text}`));
      } else {
        block.append(noteRow(time, item.text));
      }
    }
    return block;
  }

  // A line under an entry. An invisible copy of the entry's time in front of
  // it takes the same width, so the text starts where the entry's text does
  // in any font.
  function noteRow(time, text) {
    return el(
      "div",
      { class: "note" },
      el("span", { class: "time spacer", text: time, "aria-hidden": "true" }),
      el("span", { class: "text", text })
    );
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
      hit.entry ? tagged(hit.entry.text, hit.entry.tags) : el("span", { class: "text", text: hit.text.trim() }),
      ...(hit.entry?.more || []).map((line) => el("span", { class: "text more", text: line }))
    );
  }

  function render() {
    list.replaceChildren();
    sentinel.replaceChildren();
    showBanner(model.error);
    renderPlan();
    fitPlan();

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
      reviewFromButton.hidden = true;
      return;
    }

    reviewButton.hidden = false;
    reviewFromButton.hidden = !model.loaded;
    if (model.loaded) {
      reviewFromButton.textContent = fill(t.reviewFrom, { date: model.loaded.from });
      reviewFromButton.title = fill(t.reviewFromTitle, { date: model.loaded.from });
    }

    const busyText = { loading: t.loading, searching: t.searching, recording: t.recording }[model.busy];
    recordButton.disabled = model.busy === "recording";

    if (model.search) {
      const { query, results } = model.search;
      status.textContent = busyText || fill(results.length ? t.resultsFor : t.noResults, { query, count: results.length });
      list.append(el("button", { class: "link back", text: `← ${t.clearSearch}`, onclick: clearSearch }));
      // Timeline entries first, newest first; then documents.
      const { timeline, documents } = groupHits(results);
      if (timeline.length) {
        list.append(el("h2", { class: "group", text: fill(t.timelineHits, { count: timeline.length }) }));
        for (const item of timeline) list.append(hitRow(item.hit, item.index));
      }
      if (documents.length) {
        list.append(el("h2", { class: "group", text: fill(t.documentHits, { count: documents.length }) }));
        for (const item of documents) list.append(hitRow(item.hit, item.index));
      }
      return;
    }

    status.textContent = busyText || (model.loaded ? fill(t.showing, model.loaded) : "");
    for (const day of model.days) list.append(dayBlock(day));
    if (!model.days.length && !model.busy) list.append(el("p", { class: "empty", text: t.noEntries }));

    if (model.busy === "loading" && model.days.length) {
      sentinel.append(el("p", { class: "muted", text: t.loadingOlder }));
    } else if (model.hasOlder) {
      sentinel.append(
        el("button", {
          class: "more",
          text: fill(t.loadOlder, { date: model.loaded.from }),
          onclick: () => vscode.postMessage({ type: "older" }),
        })
      );
    } else {
      sentinel.append(el("p", { class: "muted", text: t.noOlder }));
    }
  }

  function afterRender(previous) {
    if (model.search) {
      if (!previous.search) timeline.scrollTop = 0;
      return;
    }
    if (previous.search) {
      timeline.scrollTop = timelineScroll;
    }
    if (model.highlight && model.highlight !== lastHighlight) {
      const target = list.querySelector(`[data-key="${CSS.escape(model.highlight)}"]`);
      if (target) target.scrollIntoView({ block: "center" });
    }
    lastHighlight = model.highlight;
  }

  // ---- loading older days -----------------------------------------------
  //
  // Only when the person scrolls to the end, or presses the button there. The
  // screen never loads older days on its own: a quiet week would otherwise
  // make it run back until something filled the screen.

  timeline.addEventListener(
    "scroll",
    () => {
      if (model.search || model.busy || !model.hasOlder) return;
      if (sentinel.getBoundingClientRect().top < timeline.getBoundingClientRect().bottom + 80) {
        vscode.postMessage({ type: "older" });
      }
    },
    { passive: true }
  );

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
      fitRecordInput();
      recordInput.focus();
    } else if (message.type === "focusRecord") {
      recordInput.focus();
    } else if (message.type === "planAdded") {
      planInput.value = "";
      planInput.focus();
    }
  });

  vscode.postMessage({ type: "ready" });
})();
