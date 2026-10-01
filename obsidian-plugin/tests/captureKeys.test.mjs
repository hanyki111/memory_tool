/**
 * Tests for the Enter-to-record wiring shared by the panel and the quick modal.
 *
 * Run with: node --test tests/
 *
 * The two paths these pin are the two that broke: Enter recorded nothing at all
 * on Android because the whole shortcut was gated on the platform, and Shift +
 * Enter must keep inserting a newline on desktop even though a line break is
 * exactly what the phone path listens for.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { bindCaptureSubmit, isLineBreakInput } from "../src/captureKeys.ts";

/**
 * The slice of a textarea the wiring touches, with a way to dispatch into it.
 *
 * `fire` reports whether a handler cancelled the default action, which is the
 * whole question for both paths: cancelling is what stops the newline from being
 * typed, and letting it through is what keeps Shift+Enter working.
 */
function fakeInput() {
  const listeners = new Map();

  return {
    attributes: {},
    recorded: 0,

    setAttribute(name, value) {
      this.attributes[name] = value;
    },

    addEventListener(type, handler) {
      const list = listeners.get(type) ?? [];
      list.push(handler);
      listeners.set(type, list);
    },

    fire(type, props = {}) {
      const event = {
        ...props,
        defaultPrevented: false,
        preventDefault() {
          event.defaultPrevented = true;
        },
      };

      for (const handler of listeners.get(type) ?? []) handler(event);
      return event.defaultPrevented;
    },
  };
}

/** A bound input on the given platform, counting the records it was asked for. */
function bound(isMobile) {
  const input = fakeInput();
  bindCaptureSubmit(input, { isMobile, submit: () => (input.recorded += 1) });
  return input;
}

// ---------------------------------------------------------------------------
// The key path -- desktop, and any phone with a hardware keyboard
// ---------------------------------------------------------------------------

test("Enter records and does not type a newline", () => {
  const input = bound(false);

  assert.equal(input.fire("keydown", { key: "Enter", keyCode: 13 }), true);
  assert.equal(input.recorded, 1);
});

test("Shift+Enter types a newline and records nothing", () => {
  const input = bound(false);

  assert.equal(input.fire("keydown", { key: "Enter", keyCode: 13, shiftKey: true }), false);
  assert.equal(input.recorded, 0);
});

test("the Enter that commits a composition is left alone", () => {
  const input = bound(false);

  input.fire("keydown", { key: "Enter", keyCode: 229, isComposing: true });
  input.fire("keydown", { key: "Process", keyCode: 229 });
  assert.equal(input.recorded, 0);

  // Chrome sends the commit's own keydown afterwards, and that one records.
  assert.equal(input.fire("keydown", { key: "Enter", keyCode: 13 }), true);
  assert.equal(input.recorded, 1);
});

test("other keys are left alone", () => {
  const input = bound(false);

  assert.equal(input.fire("keydown", { key: "a", keyCode: 65 }), false);
  assert.equal(input.recorded, 0);
});

// ---------------------------------------------------------------------------
// The line-break path -- an Android soft keyboard, which may send no key event
// ---------------------------------------------------------------------------

test("a line break records on a phone", () => {
  const input = bound(true);

  assert.equal(input.fire("beforeinput", { inputType: "insertLineBreak" }), true);
  assert.equal(input.recorded, 1);
});

test("desktop ignores the line break, so Shift+Enter survives", () => {
  const input = bound(false);

  assert.equal(input.fire("beforeinput", { inputType: "insertLineBreak" }), false);
  assert.equal(input.recorded, 0);
});

test("ordinary typing on a phone is not a record", () => {
  const input = bound(true);

  assert.equal(input.fire("beforeinput", { inputType: "insertText", data: "가" }), false);
  assert.equal(input.recorded, 0);
});

test("a line break arriving mid-composition is left alone", () => {
  const input = bound(true);

  // The box is a syllable behind here, so recording would truncate the entry.
  assert.equal(
    input.fire("beforeinput", { inputType: "insertLineBreak", isComposing: true }),
    false,
  );
  assert.equal(input.recorded, 0);
});

test("both line-break inputTypes count", () => {
  assert.equal(isLineBreakInput("insertLineBreak"), true);
  assert.equal(isLineBreakInput("insertParagraph"), true);
  assert.equal(isLineBreakInput("insertText"), false);
});

// ---------------------------------------------------------------------------
// The keyboard's own label
// ---------------------------------------------------------------------------

test("the soft keyboard is told the key sends", () => {
  assert.equal(bound(true).attributes.enterkeyhint, "send");
  assert.equal(bound(false).attributes.enterkeyhint, "send");
});
