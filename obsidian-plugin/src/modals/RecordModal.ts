import { App, Modal, Notice, Platform } from "obsidian";
import { bindCaptureSubmit } from "../captureKeys";

/**
 * Minimal capture modal.
 *
 * Deliberately close to chrome-free: no title, one input, one button. A 0.5s
 * capture has room for little else, and every pixel of framing is a pixel the
 * user looks past before typing.
 *
 * The button is not decoration. Enter records on either platform now (see
 * bindCaptureSubmit), but on a phone it is the button a thumb reaches for, and
 * it is the only control left standing once the keyboard is dismissed.
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

    const isMobile = Platform.isMobile;

    const input = contentEl.createEl("textarea", {
      cls: "memory-tool-quick-input",
      attr: {
        rows: isMobile ? "3" : "1",
        placeholder: "지금 무엇을 하고 있나요?  Enter로 기록",
      },
    });

    input.focus();

    const row = contentEl.createDiv({ cls: "memory-tool-quick-actions" });
    const submitBtn = row.createEl("button", { cls: "mod-cta", text: "기록" });
    submitBtn.addEventListener("click", () => this.submit(input.value));

    bindCaptureSubmit(input, { isMobile, submit: () => this.submit(input.value) });
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
