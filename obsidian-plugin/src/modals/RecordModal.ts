import { App, Modal, Notice, Platform } from "obsidian";

/**
 * Minimal capture modal.
 *
 * Deliberately close to chrome-free: no title, one input, one button. A 0.5s
 * capture has room for little else, and every pixel of framing is a pixel the
 * user looks past before typing.
 *
 * The button is not decoration. On a phone, Enter is the newline key and there
 * is no Shift to hold, so a keyboard-only submit would be unreachable — the
 * button is the primary control there and the shortcut is the desktop extra.
 */
export class RecordModal extends Modal {
  private record: (message: string) => Promise<{ entry: string }>;

  constructor(app: App, record: (message: string) => Promise<{ entry: string }>) {
    super(app);
    this.record = record;
  }

  onOpen() {
    const { contentEl, modalEl } = this;
    contentEl.empty();
    modalEl.addClass("memory-tool-quick-modal");

    const submitOnEnter = !Platform.isMobile;

    const input = contentEl.createEl("textarea", {
      cls: "memory-tool-quick-input",
      attr: {
        rows: submitOnEnter ? "1" : "3",
        placeholder: submitOnEnter
          ? "지금 무엇을 하고 있나요?  Enter로 기록"
          : "지금 무엇을 하고 있나요?",
      },
    });

    input.focus();

    const row = contentEl.createDiv({ cls: "memory-tool-quick-actions" });
    const submitBtn = row.createEl("button", { cls: "mod-cta", text: "기록" });
    submitBtn.addEventListener("click", () => this.submit(input.value));

    input.addEventListener("keydown", (e: KeyboardEvent) => {
      // A Korean IME fires keydown for the Enter that commits a composition.
      // Without this guard that Enter submits the entry mid-syllable and the
      // last character is silently dropped.
      if (e.isComposing || e.keyCode === 229) return;

      if (submitOnEnter && e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.submit(input.value);
      }
    });
  }

  /**
   * Close first, then write.
   *
   * The write is fast enough that waiting would only add a visible pause, and a
   * failure still surfaces as a notice carrying the original text, so nothing is
   * lost by not blocking on it.
   */
  private submit(raw: string): void {
    const text = raw.trim();
    if (!text) {
      this.close();
      return;
    }

    this.close();

    this.record(text).catch((err: any) => {
      new Notice(`기록 실패: ${err.message}\n${text}`, 10000);
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}
