/**
 * Enter-to-record wiring for the capture boxes.
 *
 * Shared by the panel and the quick modal because they are one interaction in
 * two frames: whoever learns Enter in the one will reach for it in the other,
 * and the two copies this replaces had already drifted apart.
 *
 * Two events are needed, because on a phone neither answers on its own:
 *
 *   - `keydown` is the desktop path, and the only place Shift+Enter can be let
 *     through as a newline. It ignores a composing Enter: with a Korean IME that
 *     keydown carries a syllable the box has not committed yet, so recording
 *     there drops the last character. Chrome delivers a second, non-composing
 *     keydown once the commit lands, so waiting for it costs nothing.
 *
 *   - `beforeinput` is the phone path. An Android soft keyboard is free to
 *     report its Enter as keyCode 229, or to send no key event at all, but it
 *     cannot insert the line break without announcing it here first, and
 *     cancelling that insertion is what turns the key into "record".
 *
 * The two cannot both answer one press: a keydown whose default action is
 * prevented never produces the beforeinput that would have followed it.
 */

/** What the wiring needs from its caller. */
export interface CaptureSubmitOptions {
  /** True on a phone, where the soft keyboard needs the beforeinput path. */
  isMobile: boolean;
  /** Record whatever is in the box. */
  submit: () => void;
}

/** The inputTypes that mean "Enter is about to break the line". */
export function isLineBreakInput(inputType: string): boolean {
  return inputType === "insertLineBreak" || inputType === "insertParagraph";
}

export function bindCaptureSubmit(
  input: HTMLTextAreaElement,
  options: CaptureSubmitOptions,
): void {
  // Labels the soft keyboard's action key as "send" instead of a return arrow,
  // which is now what it does on either platform.
  input.setAttribute("enterkeyhint", "send");

  input.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.isComposing || e.keyCode === 229) return;
    if (e.key !== "Enter" || e.shiftKey) return;

    e.preventDefault();
    options.submit();
  });

  // Desktop stops here. keydown already answers for every Enter it sees, and
  // taking beforeinput as well would swallow the Shift+Enter newline, which
  // arrives there with nothing on it to tell it apart from a plain Enter.
  if (!options.isMobile) return;

  input.addEventListener("beforeinput", (e: InputEvent) => {
    if (!isLineBreakInput(e.inputType)) return;

    // The keydown guard's reasoning, in the other event: with a composition
    // still open the box is a syllable behind. A soft keyboard commits before it
    // sends the line break, so this is the unusual order; falling through to a
    // newline costs one more press, where recording would cost a character.
    if (e.isComposing) return;

    e.preventDefault();
    options.submit();
  });
}
