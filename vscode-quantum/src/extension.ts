/**
 * Quantum VS Code Extension - Main Entry Point
 *
 * This extension provides comprehensive support for the Quantum Framework:
 *
 * Phase 1-2: Language Basics
 * - Syntax highlighting for .q files
 * - IntelliSense/autocomplete for tags and attributes
 * - Hover documentation
 * - Go to definition
 * - Diagnostics/validation
 * - Code snippets
 *
 * Phase 3: Tooling
 * - Preview panel (WebView)
 * - Component tree view
 * - Run/debug integration
 * - Task provider
 *
 * Phase 4: AI Assistance
 * - Explain error
 * - Suggest fix
 * - Documentation lookup
 */

import * as vscode from 'vscode';

// Phase 1-2: Language providers
import { registerCompletionProvider } from './providers/completionProvider';
import { registerHoverProvider } from './providers/hoverProvider';
import { registerDefinitionProvider } from './providers/definitionProvider';
import { registerDiagnosticsProvider } from './providers/diagnosticsProvider';

// Phase 3-4: Tooling and AI
import { activatePhase3and4, deactivatePhase3and4 } from './phase3-4-activation';

/**
 * Extension activation
 */
export function activate(context: vscode.ExtensionContext): void {
    console.log('Activating Quantum Language Support extension');

    // =====================================
    // Phase 1-2: Language Basics
    // =====================================

    // Register completion provider (IntelliSense)
    registerCompletionProvider(context);

    // Register hover provider (documentation on hover)
    registerHoverProvider(context);

    // Register definition provider (go to definition)
    registerDefinitionProvider(context);

    // Register diagnostics provider (validation/linting)
    registerDiagnosticsProvider(context);

    // =====================================
    // Phase 3-4: Tooling and AI Assistance
    // =====================================

    activatePhase3and4(context);

    // =====================================
    // Status bar item
    // =====================================

    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(circuit-board) Quantum';
    statusBarItem.tooltip = 'Quantum Framework';
    statusBarItem.command = 'quantum.runTask';
    context.subscriptions.push(statusBarItem);

    // Show status bar item when editing Quantum files
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor && editor.document.languageId === 'quantum') {
                statusBarItem.show();
            } else {
                statusBarItem.hide();
            }
        })
    );

    // Check initial editor
    if (vscode.window.activeTextEditor?.document.languageId === 'quantum') {
        statusBarItem.show();
    }

    console.log('Quantum Language Support extension activated');
}

/**
 * Extension deactivation
 */
export function deactivate(): void {
    deactivatePhase3and4();
    console.log('Quantum Language Support extension deactivated');
}
