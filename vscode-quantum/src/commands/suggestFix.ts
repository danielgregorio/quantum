/**
 * Quantum Suggest Fix Command
 *
 * Code actions for common errors:
 * - Missing required attributes -> Quick fix to add them
 * - Unclosed tags -> Quick fix to close them
 * - Uses LLM only for complex cases
 */

import * as vscode from 'vscode';
import { AIProvider, getAIProvider } from '../ai/aiProvider';
import { getSuggestFixPrompt } from '../ai/prompts';

/**
 * Code action provider for Quantum files
 */
export class QuantumCodeActionProvider implements vscode.CodeActionProvider {
    public static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix
    ];

    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<(vscode.CodeAction | vscode.Command)[]> {
        const actions: vscode.CodeAction[] = [];

        for (const diagnostic of context.diagnostics) {
            const fixes = this._getFixesForDiagnostic(document, diagnostic);
            actions.push(...fixes);
        }

        // Add AI-powered fix option if there are unresolved diagnostics
        if (context.diagnostics.length > 0 && actions.length === 0) {
            const aiAction = new vscode.CodeAction(
                'Ask AI for fix suggestion',
                vscode.CodeActionKind.QuickFix
            );
            aiAction.command = {
                command: 'quantum.suggestFixWithAI',
                title: 'Ask AI for fix suggestion',
                arguments: [document, context.diagnostics[0]]
            };
            aiAction.isPreferred = false;
            actions.push(aiAction);
        }

        return actions;
    }

    private _getFixesForDiagnostic(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];
        const message = diagnostic.message;
        const line = document.lineAt(diagnostic.range.start.line);
        const lineText = line.text;

        // Fix: Missing required attribute 'name'
        if (message.includes("Missing required attribute 'name'")) {
            const fix = this._createAddAttributeFix(document, diagnostic, lineText, 'name', 'MyName');
            if (fix) {
                actions.push(fix);
            }
        }

        // Fix: Missing required attribute 'var'
        if (message.includes("Missing required attribute 'var'")) {
            const fix = this._createAddAttributeFix(document, diagnostic, lineText, 'var', 'myVariable');
            if (fix) {
                actions.push(fix);
            }
        }

        // Fix: Missing required attribute 'value'
        if (message.includes("Missing required attribute 'value'")) {
            const fix = this._createAddAttributeFix(document, diagnostic, lineText, 'value', '');
            if (fix) {
                actions.push(fix);
            }
        }

        // Fix: Missing required attribute 'test'
        if (message.includes("Missing required attribute 'test'")) {
            const fix = this._createAddAttributeFix(document, diagnostic, lineText, 'test', 'true');
            if (fix) {
                actions.push(fix);
            }
        }

        // Fix: Missing required attribute 'src' (for include)
        if (message.includes("Missing required attribute 'src'")) {
            const fix = this._createAddAttributeFix(document, diagnostic, lineText, 'src', './component.q');
            if (fix) {
                actions.push(fix);
            }
        }

        // Fix: Unclosed tag
        if (message.includes('Unclosed tag') || message.includes('Expected closing tag')) {
            const tagMatch = lineText.match(/<(q:\w+|[\w-]+)/);
            if (tagMatch) {
                const tagName = tagMatch[1];
                const fix = this._createCloseTagFix(document, diagnostic, tagName);
                actions.push(fix);

                // Also offer to make it self-closing
                const selfCloseFix = this._createSelfClosingFix(document, diagnostic, lineText);
                if (selfCloseFix) {
                    actions.push(selfCloseFix);
                }
            }
        }

        // Fix: Unknown tag - suggest similar tags
        if (message.includes('Unknown tag')) {
            const tagMatch = message.match(/Unknown tag[:\s]+['"]?(\w+)['"]?/);
            if (tagMatch) {
                const unknownTag = tagMatch[1];
                const suggestions = this._getSimilarTags(unknownTag);

                for (const suggestion of suggestions) {
                    const fix = this._createReplaceTagFix(document, diagnostic, lineText, unknownTag, suggestion);
                    if (fix) {
                        actions.push(fix);
                    }
                }
            }
        }

        // Fix: Invalid attribute value
        if (message.includes('Invalid attribute value')) {
            const attrMatch = message.match(/attribute\s+'(\w+)'/);
            if (attrMatch) {
                const attr = attrMatch[1];
                const fix = this._createFixAttributeValueFix(document, diagnostic, lineText, attr);
                if (fix) {
                    actions.push(fix);
                }
            }
        }

        // Fix: Missing closing brace in expression
        if (message.includes('Unclosed expression') || message.includes('Missing closing brace')) {
            const fix = this._createCloseExpressionFix(document, diagnostic, lineText);
            if (fix) {
                actions.push(fix);
            }
        }

        return actions;
    }

    private _createAddAttributeFix(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic,
        lineText: string,
        attrName: string,
        defaultValue: string
    ): vscode.CodeAction | undefined {
        // Find position to insert attribute (before > or />)
        const closeMatch = lineText.match(/(\/?)>$/);
        if (!closeMatch) {
            return undefined;
        }

        const insertPos = lineText.length - closeMatch[0].length;
        const insertText = ` ${attrName}="${defaultValue}"`;

        const fix = new vscode.CodeAction(
            `Add missing '${attrName}' attribute`,
            vscode.CodeActionKind.QuickFix
        );

        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.insert(
            document.uri,
            new vscode.Position(diagnostic.range.start.line, insertPos),
            insertText
        );

        fix.isPreferred = true;
        fix.diagnostics = [diagnostic];

        return fix;
    }

    private _createCloseTagFix(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic,
        tagName: string
    ): vscode.CodeAction {
        const fix = new vscode.CodeAction(
            `Add closing tag </${tagName}>`,
            vscode.CodeActionKind.QuickFix
        );

        // Find a good position to insert the closing tag
        // (end of current line or next line)
        const line = document.lineAt(diagnostic.range.end.line);
        const insertPosition = line.range.end;

        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.insert(
            document.uri,
            insertPosition,
            `</${tagName}>`
        );

        fix.diagnostics = [diagnostic];

        return fix;
    }

    private _createSelfClosingFix(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic,
        lineText: string
    ): vscode.CodeAction | undefined {
        // Check if the tag ends with > (not />)
        if (lineText.trimEnd().endsWith('/>')) {
            return undefined;
        }

        const match = lineText.match(/>$/);
        if (!match) {
            return undefined;
        }

        const fix = new vscode.CodeAction(
            'Make tag self-closing',
            vscode.CodeActionKind.QuickFix
        );

        const replaceStart = new vscode.Position(
            diagnostic.range.start.line,
            lineText.lastIndexOf('>')
        );
        const replaceEnd = new vscode.Position(
            diagnostic.range.start.line,
            lineText.lastIndexOf('>') + 1
        );

        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.replace(
            document.uri,
            new vscode.Range(replaceStart, replaceEnd),
            '/>'
        );

        fix.diagnostics = [diagnostic];

        return fix;
    }

    private _createReplaceTagFix(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic,
        lineText: string,
        unknownTag: string,
        suggestion: string
    ): vscode.CodeAction | undefined {
        const fix = new vscode.CodeAction(
            `Replace with '${suggestion}'`,
            vscode.CodeActionKind.QuickFix
        );

        // Find and replace the tag name
        const tagRegex = new RegExp(`<${unknownTag}\\b`, 'g');
        const match = tagRegex.exec(lineText);

        if (!match) {
            return undefined;
        }

        const startPos = new vscode.Position(diagnostic.range.start.line, match.index);
        const endPos = new vscode.Position(diagnostic.range.start.line, match.index + match[0].length);

        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.replace(
            document.uri,
            new vscode.Range(startPos, endPos),
            `<${suggestion}`
        );

        fix.diagnostics = [diagnostic];

        return fix;
    }

    private _createFixAttributeValueFix(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic,
        lineText: string,
        attrName: string
    ): vscode.CodeAction | undefined {
        // Find the attribute in the line
        const attrRegex = new RegExp(`${attrName}="([^"]*)"`, 'g');
        const match = attrRegex.exec(lineText);

        if (!match) {
            return undefined;
        }

        const fix = new vscode.CodeAction(
            `Fix '${attrName}' attribute value`,
            vscode.CodeActionKind.QuickFix
        );

        // This is a placeholder - actual fix depends on the specific error
        fix.command = {
            command: 'quantum.suggestFixWithAI',
            title: 'Suggest fix with AI',
            arguments: [document, diagnostic]
        };

        fix.diagnostics = [diagnostic];

        return fix;
    }

    private _createCloseExpressionFix(
        document: vscode.TextDocument,
        diagnostic: vscode.Diagnostic,
        lineText: string
    ): vscode.CodeAction | undefined {
        // Find unclosed expression
        const exprMatch = lineText.match(/\{([^}]*$)/);
        if (!exprMatch) {
            return undefined;
        }

        const fix = new vscode.CodeAction(
            'Add closing brace to expression',
            vscode.CodeActionKind.QuickFix
        );

        const insertPos = new vscode.Position(
            diagnostic.range.start.line,
            lineText.length
        );

        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.insert(document.uri, insertPos, '}');

        fix.isPreferred = true;
        fix.diagnostics = [diagnostic];

        return fix;
    }

    private _getSimilarTags(unknownTag: string): string[] {
        const quantumTags = [
            'q:component', 'q:set', 'q:output', 'q:if', 'q:else', 'q:elseif',
            'q:loop', 'q:function', 'q:call', 'q:query', 'q:param',
            'q:action', 'q:form', 'q:input', 'q:button', 'q:select',
            'q:include', 'q:slot', 'q:template', 'q:file', 'q:mail',
            'q:try', 'q:catch', 'q:finally', 'q:throw'
        ];

        // Simple string similarity (Levenshtein-like)
        const scored = quantumTags.map(tag => ({
            tag,
            score: this._similarity(unknownTag.toLowerCase(), tag.toLowerCase())
        }));

        scored.sort((a, b) => b.score - a.score);

        return scored.slice(0, 3).filter(s => s.score > 0.3).map(s => s.tag);
    }

    private _similarity(s1: string, s2: string): number {
        const longer = s1.length > s2.length ? s1 : s2;
        const shorter = s1.length > s2.length ? s2 : s1;

        if (longer.length === 0) {
            return 1.0;
        }

        const costs: number[] = [];
        for (let i = 0; i <= shorter.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= longer.length; j++) {
                if (i === 0) {
                    costs[j] = j;
                } else if (j > 0) {
                    let newValue = costs[j - 1];
                    if (shorter.charAt(i - 1) !== longer.charAt(j - 1)) {
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    }
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
            if (i > 0) {
                costs[longer.length] = lastValue;
            }
        }

        return (longer.length - costs[longer.length]) / longer.length;
    }
}

/**
 * AI-powered fix suggestion
 */
export async function suggestFixWithAI(
    document: vscode.TextDocument,
    diagnostic: vscode.Diagnostic
): Promise<void> {
    const aiProvider = getAIProvider();

    if (!aiProvider.isAvailable()) {
        vscode.window.showWarningMessage(
            'AI provider is not configured. Please configure quantum.ai settings.',
            'Open Settings'
        ).then(result => {
            if (result === 'Open Settings') {
                vscode.commands.executeCommand('workbench.action.openSettings', 'quantum.ai');
            }
        });
        return;
    }

    // Get context around the error
    const startLine = Math.max(0, diagnostic.range.start.line - 5);
    const endLine = Math.min(document.lineCount - 1, diagnostic.range.end.line + 5);

    const codeLines: string[] = [];
    for (let i = startLine; i <= endLine; i++) {
        const prefix = i === diagnostic.range.start.line ? '>>> ' : '    ';
        codeLines.push(`${prefix}${i + 1}: ${document.lineAt(i).text}`);
    }

    const context = {
        errorMessage: diagnostic.message,
        code: codeLines.join('\n'),
        fileName: document.fileName
    };

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Getting AI suggestion...',
        cancellable: false
    }, async () => {
        try {
            const prompt = getSuggestFixPrompt(context);
            const suggestion = await aiProvider.complete(prompt);

            // Parse the suggestion and apply it
            const edit = parseSuggestionToEdit(document, diagnostic, suggestion);

            if (edit) {
                const result = await vscode.window.showInformationMessage(
                    'AI suggests this fix. Apply it?',
                    { modal: true, detail: suggestion },
                    'Apply',
                    'Copy to Clipboard'
                );

                if (result === 'Apply') {
                    await vscode.workspace.applyEdit(edit);
                } else if (result === 'Copy to Clipboard') {
                    await vscode.env.clipboard.writeText(suggestion);
                }
            } else {
                vscode.window.showInformationMessage(
                    'AI Suggestion',
                    { modal: true, detail: suggestion }
                );
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to get AI suggestion: ${error}`);
        }
    });
}

/**
 * Try to parse AI suggestion into a workspace edit
 */
function parseSuggestionToEdit(
    document: vscode.TextDocument,
    diagnostic: vscode.Diagnostic,
    suggestion: string
): vscode.WorkspaceEdit | undefined {
    // Look for code blocks in the suggestion
    const codeBlockMatch = suggestion.match(/```(?:xml|quantum)?\n?([\s\S]*?)```/);

    if (codeBlockMatch) {
        const suggestedCode = codeBlockMatch[1].trim();
        const edit = new vscode.WorkspaceEdit();

        // Replace the error line with the suggested code
        const line = document.lineAt(diagnostic.range.start.line);
        edit.replace(document.uri, line.range, suggestedCode);

        return edit;
    }

    return undefined;
}

/**
 * Register the suggest fix commands and code action provider
 */
export function registerSuggestFixProvider(context: vscode.ExtensionContext): void {
    // Register code action provider
    context.subscriptions.push(
        vscode.languages.registerCodeActionsProvider(
            { language: 'quantum', scheme: 'file' },
            new QuantumCodeActionProvider(),
            {
                providedCodeActionKinds: QuantumCodeActionProvider.providedCodeActionKinds
            }
        )
    );

    // Register AI fix command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.suggestFixWithAI', suggestFixWithAI)
    );

    // Register general suggest fix command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.suggestFix', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            const diagnostics = vscode.languages.getDiagnostics(editor.document.uri);
            const diagnostic = diagnostics.find(d => d.range.contains(editor.selection.active));

            if (diagnostic) {
                await suggestFixWithAI(editor.document, diagnostic);
            } else {
                vscode.window.showInformationMessage('No error at current position');
            }
        })
    );
}
