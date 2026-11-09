/**
 * Memory Tool Timeline: the side bar view and editor tabs, on the knowledge
 * base of the folder open in this window.
 */

import * as path from "node:path";
import * as vscode from "vscode";

import { MemoryToolCli, findPython } from "./cli.ts";
import type { Notice } from "./cli.ts";
import { newNonce, page } from "./html.ts";
import { earliestDate } from "./kb.ts";
import { Screen } from "./screen.ts";
import type { ScreenHost, Session } from "./screen.ts";
import { stringsFor } from "./strings.ts";

const VIEW_ID = "memoryTool.timeline";

class Extension {
  private readonly context: vscode.ExtensionContext;
  private readonly strings = stringsFor(vscode.env.language);
  private readonly screens = new Set<Screen>();
  private session: Session = { status: "nofolder", cli: null, earliest: null };
  private watcher: vscode.FileSystemWatcher | null = null;
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;
  private ready: Promise<void>;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    this.ready = this.connect();
  }

  // ---- the knowledge base -------------------------------------------------

  /** The folder the CLI runs in: the first folder of the window. */
  private folder(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  private async connect(): Promise<void> {
    this.watcher?.dispose();
    this.watcher = null;

    const folder = this.folder();
    if (!folder) {
      this.session = { status: "nofolder", cli: null, earliest: null };
      return;
    }

    const configured = vscode.workspace.getConfiguration("memoryTool").get<string>("python", "");
    const cli = new MemoryToolCli({ python: findPython(configured, folder), cwd: folder });

    try {
      const info = await cli.base();
      if (!info.found) {
        this.session = { status: "nobase", cli: null, earliest: null };
        return;
      }
      this.session = { status: "ready", cli, earliest: earliestDate(info.base) };
      this.watch(info.base);
    } catch (error) {
      // Keep the CLI so the screen shows why it failed, such as a missing Python.
      this.session = { status: "ready", cli, earliest: null };
      void vscode.window.showErrorMessage(`Memory Tool: ${(error as Error).message}`);
    }
  }

  /** Redraw every screen when a timeline file changes, whoever changed it. */
  private watch(base: string): void {
    const pattern = new vscode.RelativePattern(vscode.Uri.file(path.join(base, "timeline")), "**/*.md");
    this.watcher = vscode.workspace.createFileSystemWatcher(pattern);
    const changed = () => this.scheduleRefresh(base);
    this.watcher.onDidChange(changed);
    this.watcher.onDidCreate(changed);
    this.watcher.onDidDelete(changed);
    this.context.subscriptions.push(this.watcher);
  }

  private scheduleRefresh(base: string): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    // One file write can fire several events; wait for them to settle.
    this.refreshTimer = setTimeout(() => {
      this.refreshTimer = null;
      this.session.earliest = earliestDate(base);
      for (const screen of this.screens) {
        void screen.refresh();
      }
    }, 300);
  }

  async reconnect(): Promise<void> {
    this.ready = this.connect();
    await this.ready;
    for (const screen of this.screens) {
      void screen.restart(this.session);
    }
  }

  // ---- screens ------------------------------------------------------------

  private html(webview: vscode.Webview, inEditor: boolean): string {
    const media = vscode.Uri.joinPath(this.context.extensionUri, "media");
    return page({
      cspSource: webview.cspSource,
      scriptUri: webview.asWebviewUri(vscode.Uri.joinPath(media, "timeline.js")).toString(),
      logicUri: webview.asWebviewUri(vscode.Uri.joinPath(media, "logic.js")).toString(),
      styleUri: webview.asWebviewUri(vscode.Uri.joinPath(media, "timeline.css")).toString(),
      nonce: newNonce(),
      strings: this.strings,
      inEditor,
      language: vscode.env.language,
    });
  }

  /** Put a screen in a webview and keep it until the webview goes away. */
  attach(webview: vscode.Webview, inEditor: boolean, onDispose: (listener: () => void) => vscode.Disposable): void {
    webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, "media")],
    };

    let screen: Screen;
    const host: ScreenHost = {
      post: (message) => void webview.postMessage(message),
      openFile: (file, line) => void this.openFile(file, line),
      notify: (notices) => this.notify(notices),
      review: (since) => this.review(since),
      widen: () => this.openInEditor(),
      recorded: () => {
        for (const other of this.screens) {
          if (other !== screen) void other.refresh();
        }
      },
    };
    screen = new Screen(host, this.session, this.strings);
    this.screens.add(screen);

    const subscription = webview.onDidReceiveMessage(async (message) => {
      await this.ready;
      // The screen was made before the knowledge base was found; start it on
      // the session as it is now.
      if (message?.type === "ready") {
        await screen.restart(this.session);
      } else {
        await screen.handle(message);
      }
    });
    onDispose(() => {
      this.screens.delete(screen);
      subscription.dispose();
    });

    webview.html = this.html(webview, inEditor);
  }

  openInEditor(): void {
    const panel = vscode.window.createWebviewPanel(
      "memoryTool.timelinePanel",
      this.strings.tabTitle,
      vscode.ViewColumn.Active,
      { retainContextWhenHidden: true }
    );
    panel.iconPath = vscode.Uri.joinPath(this.context.extensionUri, "media", "icon.svg");
    this.attach(panel.webview, true, (listener) => panel.onDidDispose(listener));
  }

  // ---- what screens ask for ----------------------------------------------

  private async openFile(file: string, line: number): Promise<void> {
    try {
      const document = await vscode.workspace.openTextDocument(vscode.Uri.file(file));
      const position = new vscode.Position(Math.max(0, line - 1), 0);
      await vscode.window.showTextDocument(document, {
        selection: new vscode.Range(position, position),
        preview: true,
      });
    } catch (error) {
      void vscode.window.showErrorMessage(`Memory Tool: ${(error as Error).message}`);
    }
  }

  private notify(notices: Notice[]): void {
    for (const notice of notices) {
      void vscode.window.showInformationMessage(notice.message);
    }
  }

  /** Run the review in a terminal of its own; it asks questions as it goes. */
  private review(since: string | null): void {
    const cli = this.session.cli;
    if (!cli) {
      return;
    }
    const [python, ...args] = cli.reviewCommand(since);
    // Python is the terminal's process, so no shell has to quote anything.
    const terminal = vscode.window.createTerminal({
      name: since ? `mreview --since ${since}` : "mreview",
      shellPath: python,
      shellArgs: args,
      cwd: cli.cwd,
      env: { PYTHONIOENCODING: "utf-8" },
    });
    terminal.show();
  }
}

let extension: Extension | null = null;

export function activate(context: vscode.ExtensionContext): void {
  const current = new Extension(context);
  extension = current;

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      VIEW_ID,
      {
        resolveWebviewView(view) {
          current.attach(view.webview, false, (listener) => view.onDidDispose(listener));
        },
      },
      { webviewOptions: { retainContextWhenHidden: true } }
    ),
    vscode.commands.registerCommand("memoryTool.openTimeline", () => current.openInEditor()),
    vscode.commands.registerCommand("memoryTool.refresh", () => current.reconnect()),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("memoryTool.python")) {
        void current.reconnect();
      }
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => void current.reconnect())
  );
}

export function deactivate(): void {
  extension = null;
}
