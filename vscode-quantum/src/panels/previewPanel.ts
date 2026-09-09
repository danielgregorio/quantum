/**
 * Quantum Preview Panel
 *
 * WebView panel showing rendered .q output with live updates.
 * Supports both HTML view and rendered view toggle.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as cp from 'child_process';

export class QuantumPreviewPanel {
    public static currentPanel: QuantumPreviewPanel | undefined;
    public static readonly viewType = 'quantumPreview';

    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _currentDocument: vscode.TextDocument | undefined;
    private _viewMode: 'rendered' | 'html' = 'rendered';
    private _updateTimeout: NodeJS.Timeout | undefined;
    private _pythonPath: string;
    private _quantumPath: string;

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        // Get configuration
        const config = vscode.workspace.getConfiguration('quantum');
        this._pythonPath = config.get<string>('pythonPath') || 'python';
        this._quantumPath = config.get<string>('frameworkPath') || '';

        // Set initial HTML
        this._update();

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => this._handleMessage(message),
            null,
            this._disposables
        );

        // Handle disposal
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle visibility changes
        this._panel.onDidChangeViewState(
            () => {
                if (this._panel.visible) {
                    this._update();
                }
            },
            null,
            this._disposables
        );
    }

    public static createOrShow(extensionUri: vscode.Uri): QuantumPreviewPanel {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn! + 1
            : vscode.ViewColumn.Two;

        // If we already have a panel, show it
        if (QuantumPreviewPanel.currentPanel) {
            QuantumPreviewPanel.currentPanel._panel.reveal(column);
            return QuantumPreviewPanel.currentPanel;
        }

        // Otherwise, create a new panel
        const panel = vscode.window.createWebviewPanel(
            QuantumPreviewPanel.viewType,
            'Quantum Preview',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.joinPath(extensionUri, 'media'),
                    vscode.Uri.joinPath(extensionUri, 'out')
                ]
            }
        );

        QuantumPreviewPanel.currentPanel = new QuantumPreviewPanel(panel, extensionUri);
        return QuantumPreviewPanel.currentPanel;
    }

    public static revive(panel: vscode.WebviewPanel, extensionUri: vscode.Uri): void {
        QuantumPreviewPanel.currentPanel = new QuantumPreviewPanel(panel, extensionUri);
    }

    public updateDocument(document: vscode.TextDocument): void {
        this._currentDocument = document;
        this._scheduleUpdate();
    }

    public toggleViewMode(): void {
        this._viewMode = this._viewMode === 'rendered' ? 'html' : 'rendered';
        this._update();
    }

    public refresh(): void {
        this._update();
    }

    private _scheduleUpdate(): void {
        // Debounce updates
        if (this._updateTimeout) {
            clearTimeout(this._updateTimeout);
        }
        this._updateTimeout = setTimeout(() => {
            this._update();
        }, 300);
    }

    private async _update(): Promise<void> {
        if (!this._currentDocument) {
            this._panel.webview.html = this._getLoadingHtml();
            return;
        }

        try {
            const content = this._currentDocument.getText();
            const result = await this._parseQuantumContent(content);

            if (result.error) {
                this._panel.webview.html = this._getErrorHtml(result.error);
            } else {
                this._panel.webview.html = this._getPreviewHtml(result.html, result.rawHtml);
            }
        } catch (error) {
            this._panel.webview.html = this._getErrorHtml(String(error));
        }
    }

    private async _parseQuantumContent(content: string): Promise<{ html?: string; rawHtml?: string; error?: string }> {
        // Try Python parser first if available
        if (this._quantumPath) {
            try {
                const result = await this._parseWithPython(content);
                return result;
            } catch (error) {
                console.log('Python parser failed, using JS parser:', error);
            }
        }

        // Fallback to embedded JS parser
        return this._parseWithJS(content);
    }

    private _parseWithPython(content: string): Promise<{ html?: string; rawHtml?: string; error?: string }> {
        return new Promise((resolve) => {
            const pythonScript = `
import sys
import json
sys.path.insert(0, '${this._quantumPath.replace(/\\/g, '\\\\')}')

try:
    from src.core.parser import QuantumParser
    from src.runtime.renderer import QuantumRenderer

    content = '''${content.replace(/'/g, "\\'")}'''

    parser = QuantumParser()
    ast = parser.parse(content)

    renderer = QuantumRenderer()
    html = renderer.render(ast)

    print(json.dumps({"html": html, "rawHtml": html}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
`;

            const proc = cp.spawn(this._pythonPath, ['-c', pythonScript], {
                cwd: this._quantumPath
            });

            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            proc.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            proc.on('close', (code) => {
                if (code === 0 && stdout) {
                    try {
                        resolve(JSON.parse(stdout));
                    } catch {
                        resolve({ error: 'Failed to parse Python output' });
                    }
                } else {
                    resolve({ error: stderr || 'Python parser failed' });
                }
            });

            proc.on('error', (err) => {
                resolve({ error: err.message });
            });
        });
    }

    private _parseWithJS(content: string): { html?: string; rawHtml?: string; error?: string } {
        try {
            const parser = new SimpleQuantumParser();
            const result = parser.parse(content);
            return { html: result.html, rawHtml: result.rawHtml };
        } catch (error) {
            return { error: String(error) };
        }
    }

    private _handleMessage(message: { command: string; [key: string]: unknown }): void {
        switch (message.command) {
            case 'toggleView':
                this.toggleViewMode();
                break;
            case 'refresh':
                this.refresh();
                break;
            case 'copyHtml':
                if (message.html) {
                    vscode.env.clipboard.writeText(String(message.html));
                    vscode.window.showInformationMessage('HTML copied to clipboard');
                }
                break;
        }
    }

    private _getLoadingHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum Preview</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        .loading {
            text-align: center;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--vscode-editorWidget-border);
            border-top-color: var(--vscode-button-background);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="loading">
        <div class="spinner"></div>
        <p>Open a .q file to preview</p>
    </div>
</body>
</html>`;
    }

    private _getErrorHtml(error: string): string {
        const escapedError = this._escapeHtml(error);
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum Preview - Error</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        .error-container {
            border: 1px solid var(--vscode-inputValidation-errorBorder);
            background: var(--vscode-inputValidation-errorBackground);
            padding: 16px;
            border-radius: 4px;
        }
        .error-title {
            color: var(--vscode-errorForeground);
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .error-message {
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
            white-space: pre-wrap;
            word-break: break-word;
        }
        .toolbar {
            margin-bottom: 16px;
        }
        button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 2px;
        }
        button:hover {
            background: var(--vscode-button-hoverBackground);
        }
    </style>
</head>
<body>
    <div class="toolbar">
        <button onclick="refresh()">Refresh</button>
    </div>
    <div class="error-container">
        <div class="error-title">
            <span>Parse Error</span>
        </div>
        <div class="error-message">${escapedError}</div>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        function refresh() {
            vscode.postMessage({ command: 'refresh' });
        }
    </script>
</body>
</html>`;
    }

    private _getPreviewHtml(renderedHtml: string | undefined, rawHtml: string | undefined): string {
        const styleUri = this._panel.webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'media', 'preview.css')
        );

        const escapedRaw = this._escapeHtml(rawHtml || '');
        const safeRendered = renderedHtml || '';

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum Preview</title>
    <link href="${styleUri}" rel="stylesheet">
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 0;
            margin: 0;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        .toolbar {
            position: sticky;
            top: 0;
            background: var(--vscode-editorWidget-background);
            border-bottom: 1px solid var(--vscode-editorWidget-border);
            padding: 8px 16px;
            display: flex;
            gap: 8px;
            z-index: 100;
        }
        button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 2px;
            font-size: 12px;
        }
        button:hover {
            background: var(--vscode-button-hoverBackground);
        }
        button.active {
            background: var(--vscode-button-secondaryBackground);
        }
        .preview-container {
            padding: 16px;
        }
        .html-view {
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
            white-space: pre-wrap;
            background: var(--vscode-textCodeBlock-background);
            padding: 16px;
            border-radius: 4px;
            overflow-x: auto;
        }
        .rendered-view {
            background: white;
            color: black;
            padding: 16px;
            border-radius: 4px;
            min-height: 200px;
        }
        .view-label {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
    <div class="toolbar">
        <button id="btnRendered" class="${this._viewMode === 'rendered' ? 'active' : ''}" onclick="setView('rendered')">
            Rendered
        </button>
        <button id="btnHtml" class="${this._viewMode === 'html' ? 'active' : ''}" onclick="setView('html')">
            HTML
        </button>
        <button onclick="refresh()">Refresh</button>
        <button onclick="copyHtml()">Copy HTML</button>
    </div>
    <div class="preview-container">
        <div id="renderedView" style="display: ${this._viewMode === 'rendered' ? 'block' : 'none'}">
            <div class="view-label">Rendered Output</div>
            <div class="rendered-view">
                ${safeRendered}
            </div>
        </div>
        <div id="htmlView" style="display: ${this._viewMode === 'html' ? 'block' : 'none'}">
            <div class="view-label">HTML Source</div>
            <div class="html-view">${escapedRaw}</div>
        </div>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        const rawHtml = ${JSON.stringify(rawHtml || '')};

        function setView(mode) {
            document.getElementById('renderedView').style.display = mode === 'rendered' ? 'block' : 'none';
            document.getElementById('htmlView').style.display = mode === 'html' ? 'block' : 'none';
            document.getElementById('btnRendered').className = mode === 'rendered' ? 'active' : '';
            document.getElementById('btnHtml').className = mode === 'html' ? 'active' : '';
            vscode.postMessage({ command: 'toggleView' });
        }

        function refresh() {
            vscode.postMessage({ command: 'refresh' });
        }

        function copyHtml() {
            vscode.postMessage({ command: 'copyHtml', html: rawHtml });
        }
    </script>
</body>
</html>`;
    }

    private _escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    public dispose(): void {
        QuantumPreviewPanel.currentPanel = undefined;

        if (this._updateTimeout) {
            clearTimeout(this._updateTimeout);
        }

        this._panel.dispose();

        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}

/**
 * Simple embedded JavaScript parser for Quantum files
 * Used as fallback when Python parser is not available
 */
class SimpleQuantumParser {
    parse(content: string): { html: string; rawHtml: string } {
        const lines = content.split('\n');
        const htmlParts: string[] = [];
        const variables: Map<string, string> = new Map();

        for (const line of lines) {
            const trimmed = line.trim();

            // Skip empty lines and comments
            if (!trimmed || trimmed.startsWith('<!--')) {
                continue;
            }

            // Parse q:component
            const componentMatch = trimmed.match(/<q:component\s+name="([^"]+)"[^>]*>/);
            if (componentMatch) {
                htmlParts.push(`<!-- Component: ${componentMatch[1]} -->`);
                continue;
            }

            // Parse q:set
            const setMatch = trimmed.match(/<q:set\s+var="([^"]+)"\s+value="([^"]*)"[^>]*\/?>/);
            if (setMatch) {
                variables.set(setMatch[1], setMatch[2]);
                continue;
            }

            // Parse q:output
            const outputMatch = trimmed.match(/<q:output\s+value="([^"]+)"[^>]*\/?>/);
            if (outputMatch) {
                let value = outputMatch[1];
                // Replace variable references
                value = value.replace(/\{(\w+)\}/g, (_, varName) => {
                    return variables.get(varName) || `{${varName}}`;
                });
                htmlParts.push(`<span>${this._escapeHtml(value)}</span>`);
                continue;
            }

            // Parse q:if
            const ifMatch = trimmed.match(/<q:if\s+test="([^"]+)"[^>]*>/);
            if (ifMatch) {
                htmlParts.push(`<!-- if: ${ifMatch[1]} -->`);
                continue;
            }

            // Parse q:loop
            const loopMatch = trimmed.match(/<q:loop\s+from="([^"]+)"\s+to="([^"]+)"[^>]*>/);
            if (loopMatch) {
                htmlParts.push(`<!-- loop: ${loopMatch[1]} to ${loopMatch[2]} -->`);
                continue;
            }

            // Parse q:function
            const funcMatch = trimmed.match(/<q:function\s+name="([^"]+)"[^>]*>/);
            if (funcMatch) {
                htmlParts.push(`<!-- function: ${funcMatch[1]} -->`);
                continue;
            }

            // Parse HTML elements with databinding
            if (trimmed.startsWith('<') && !trimmed.startsWith('<q:') && !trimmed.startsWith('</q:')) {
                let html = trimmed;
                // Replace databinding expressions
                html = html.replace(/\{(\w+)\}/g, (_, varName) => {
                    return variables.get(varName) || `{${varName}}`;
                });
                htmlParts.push(html);
            }
        }

        const rawHtml = htmlParts.join('\n');
        return { html: rawHtml, rawHtml };
    }

    private _escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
}
