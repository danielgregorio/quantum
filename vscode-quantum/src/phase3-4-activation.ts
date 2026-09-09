/**
 * Phase 3-4 Extension Activation
 *
 * This file registers all Phase 3 (Tooling) and Phase 4 (AI Assistance) features.
 * Import and call these functions from the main extension.ts activate() function.
 */

import * as vscode from 'vscode';

// Phase 3: Tooling
import { QuantumPreviewPanel } from './panels/previewPanel';
import { registerComponentTreeView } from './views/componentTreeView';
import { registerRunCommands, initializeOutputChannel } from './commands/runCommand';
import { registerQuantumTasks } from './tasks/quantumTasks';

// Phase 4: AI Assistance
import { registerExplainErrorCommand } from './commands/explainError';
import { registerSuggestFixProvider } from './commands/suggestFix';
import { registerDocumentationLookup } from './commands/documentationLookup';
import { registerAIProviderConfiguration } from './ai/aiProvider';

/**
 * Activate Phase 3 features (Tooling)
 */
export function activatePhase3(context: vscode.ExtensionContext): void {
    console.log('Activating Quantum Phase 3: Tooling');

    // Initialize output channel
    const outputChannel = initializeOutputChannel();
    context.subscriptions.push(outputChannel);

    // Register Preview Panel commands
    registerPreviewCommands(context);

    // Register Component Tree View
    registerComponentTreeView(context);

    // Register Run/Debug commands
    registerRunCommands(context);

    // Register Task Provider
    registerQuantumTasks(context);

    // Listen for document changes to update preview
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument(event => {
            if (event.document.languageId === 'quantum') {
                if (QuantumPreviewPanel.currentPanel) {
                    QuantumPreviewPanel.currentPanel.updateDocument(event.document);
                }
            }
        })
    );

    // Listen for active editor changes
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor && editor.document.languageId === 'quantum') {
                if (QuantumPreviewPanel.currentPanel) {
                    QuantumPreviewPanel.currentPanel.updateDocument(editor.document);
                }
            }
        })
    );

    console.log('Quantum Phase 3 activated');
}

/**
 * Activate Phase 4 features (AI Assistance)
 */
export function activatePhase4(context: vscode.ExtensionContext): void {
    console.log('Activating Quantum Phase 4: AI Assistance');

    // Register AI provider configuration listener
    registerAIProviderConfiguration(context);

    // Register Explain Error command
    registerExplainErrorCommand(context);

    // Register Suggest Fix provider and commands
    registerSuggestFixProvider(context);

    // Register Documentation Lookup command
    registerDocumentationLookup(context);

    console.log('Quantum Phase 4 activated');
}

/**
 * Register preview panel commands
 */
function registerPreviewCommands(context: vscode.ExtensionContext): void {
    // Open preview command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.openPreview', () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.languageId === 'quantum') {
                const panel = QuantumPreviewPanel.createOrShow(context.extensionUri);
                panel.updateDocument(editor.document);
            } else {
                vscode.window.showErrorMessage('Please open a Quantum file to preview');
            }
        })
    );

    // Open preview to side command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.openPreviewToSide', () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.languageId === 'quantum') {
                const panel = QuantumPreviewPanel.createOrShow(context.extensionUri);
                panel.updateDocument(editor.document);
            } else {
                vscode.window.showErrorMessage('Please open a Quantum file to preview');
            }
        })
    );

    // Refresh preview command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.refreshPreview', () => {
            if (QuantumPreviewPanel.currentPanel) {
                QuantumPreviewPanel.currentPanel.refresh();
            }
        })
    );

    // Toggle preview view command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.togglePreviewView', () => {
            if (QuantumPreviewPanel.currentPanel) {
                QuantumPreviewPanel.currentPanel.toggleViewMode();
            }
        })
    );

    // Register webview serializer for persistence
    if (vscode.window.registerWebviewPanelSerializer) {
        context.subscriptions.push(
            vscode.window.registerWebviewPanelSerializer(QuantumPreviewPanel.viewType, {
                async deserializeWebviewPanel(webviewPanel: vscode.WebviewPanel, state: unknown) {
                    QuantumPreviewPanel.revive(webviewPanel, context.extensionUri);

                    // Restore document if available
                    const editor = vscode.window.activeTextEditor;
                    if (editor && editor.document.languageId === 'quantum') {
                        QuantumPreviewPanel.currentPanel?.updateDocument(editor.document);
                    }
                }
            })
        );
    }
}

/**
 * Deactivate Phase 3-4 features
 */
export function deactivatePhase3and4(): void {
    // Dispose of any resources
    if (QuantumPreviewPanel.currentPanel) {
        QuantumPreviewPanel.currentPanel.dispose();
    }

    console.log('Quantum Phase 3-4 deactivated');
}

/**
 * Full activation function - call this from main extension.ts
 *
 * Example usage in extension.ts:
 *
 * ```typescript
 * import { activatePhase3and4, deactivatePhase3and4 } from './phase3-4-activation';
 *
 * export function activate(context: vscode.ExtensionContext) {
 *     // Phase 1-2 activation...
 *
 *     // Phase 3-4 activation
 *     activatePhase3and4(context);
 * }
 *
 * export function deactivate() {
 *     deactivatePhase3and4();
 * }
 * ```
 */
export function activatePhase3and4(context: vscode.ExtensionContext): void {
    activatePhase3(context);
    activatePhase4(context);
}
