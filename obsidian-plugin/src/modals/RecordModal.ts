import { App, Modal, Notice } from "obsidian";

/**
 * Minimal capture modal.
 *
 * Deliberately chrome-free: no title, no buttons. A 0.5s capture has room for an
 * input and nothing else, and every pixel of framing is a pixel the user has to
 * look past before typing. Enter records, Esc cancels (Obsidian's own binding).
 *
 * The side panel's capture box is the better default -- it needs no opening step
 * at all -- but the modal stays for hotkey-driven capture from anywhere.
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

    const input = contentEl.createEl("textarea", {
      cls: "memory-tool-quick-input",
      attr: {
        rows: "1",
        placeholder: "지금 무엇을 하고 있나요?  Enter로 기록",
      },
    });

    input.focus();

    input.addEventListener("keydown", (e: KeyboardEvent) => {
      // A Korean IME fires keydown for the Enter that commits a composition.
      // Without this guard that Enter submits the entry mid-syllable and the
      // last character is silently dropped.
      if (e.isComposing || e.keyCode === 229) return;

      if (e.key === "Enter" && !e.shiftKey) {
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
