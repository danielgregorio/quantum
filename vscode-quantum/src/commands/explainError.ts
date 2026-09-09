/**
 * Quantum Explain Error Command
 *
 * AI-powered error explanation:
 * - Right-click on error -> "Explain Error"
 * - Sends error context to LLM
 * - Shows explanation in panel
 */

import * as vscode from 'vscode';
import { AIProvider, getAIProvider } from '../ai/aiProvider';
import { getErrorExplanationPrompt } from '../ai/prompts';

let explanationPanel: vscode.WebviewPanel | undefined;

/**
 * Extract error context from the document
 */
interface ErrorContext {
    errorMessage: string;
    errorRange: vscode.Range;
    surroundingCode: string;
    tagContext: string;
    documentPath: string;
}

/**
 * Get error context from diagnostics
 */
function getErrorContext(document: vscode.TextDocument, position: vscode.Position): ErrorContext | undefined {
    const diagnostics = vscode.languages.getDiagnostics(document.uri);

    // Find diagnostic at or near the position
    const diagnostic = diagnostics.find(d => {
        return d.range.contains(position) ||
            (d.range.start.line === position.line);
    });

    if (!diagnostic) {
        return undefined;
    }

    // Get surrounding code (5 lines before and after)
    const startLine = Math.max(0, diagnostic.range.start.line - 5);
    const endLine = Math.min(document.lineCount - 1, diagnostic.range.end.line + 5);

    const surroundingLines: string[] = [];
    for (let i = startLine; i <= endLine; i++) {
        const prefix = i === diagnostic.range.start.line ? '>>> ' : '    ';
        surroundingLines.push(`${prefix}${i + 1}: ${document.lineAt(i).text}`);
    }

    // Try to identify the tag context
    const errorLine = document.lineAt(diagnostic.range.start.line).text;
    const tagMatch = errorLine.match(/<(q:\w+|[\w-]+)[^>]*>/);
    const tagContext = tagMatch ? tagMatch[1] : 'unknown';

    return {
        errorMessage: diagnostic.message,
        errorRange: diagnostic.range,
        surroundingCode: surroundingLines.join('\n'),
        tagContext,
        documentPath: document.uri.fsPath
    };
}

/**
 * Show error explanation in a panel
 */
function showExplanation(explanation: string, errorContext: ErrorContext): void {
    if (!explanationPanel) {
        explanationPanel = vscode.window.createWebviewPanel(
            'quantumErrorExplanation',
            'Error Explanation',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        explanationPanel.onDidDispose(() => {
            explanationPanel = undefined;
        });
    }

    const html = getExplanationHtml(explanation, errorContext);
    explanationPanel.webview.html = html;
    explanationPanel.reveal();
}

/**
 * Generate HTML for the explanation panel
 */
function getExplanationHtml(explanation: string, errorContext: ErrorContext): string {
    const escapedExplanation = explanation
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    const escapedCode = errorContext.surroundingCode
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error Explanation</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            line-height: 1.6;
        }
        h2 {
            color: var(--vscode-errorForeground);
            border-bottom: 1px solid var(--vscode-editorWidget-border);
            padding-bottom: 8px;
        }
        h3 {
            color: var(--vscode-foreground);
            margin-top: 24px;
        }
        .error-message {
            background: var(--vscode-inputValidation-errorBackground);
            border: 1px solid var(--vscode-inputValidation-errorBorder);
            padding: 12px;
            border-radius: 4px;
            font-family: var(--vscode-editor-font-family);
            margin-bottom: 16px;
        }
        .code-block {
            background: var(--vscode-textCodeBlock-background);
            padding: 12px;
            border-radius: 4px;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
            overflow-x: auto;
            white-space: pre;
            margin-bottom: 16px;
        }
        .explanation {
            background: var(--vscode-textBlockQuote-background);
            border-left: 4px solid var(--vscode-textBlockQuote-border);
            padding: 12px 16px;
            margin: 16px 0;
        }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: var(--vscode-editor-font-family);
        }
        .highlight-line {
            background: var(--vscode-editor-findMatchHighlightBackground);
        }
        .tag-badge {
            display: inline-block;
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            margin-left: 8px;
        }
    </style>
</head>
<body>
    <h2>Error Explanation <span class="tag-badge">${errorContext.tagContext}</span></h2>

    <h3>Error Message</h3>
    <div class="error-message">${errorContext.errorMessage}</div>

    <h3>Code Context</h3>
    <div class="code-block">${escapedCode}</div>

    <h3>Explanation</h3>
    <div class="explanation">${escapedExplanation}</div>
</body>
</html>`;
}

/**
 * Main command: Explain Error
 */
export async function explainError(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'quantum') {
        vscode.window.showErrorMessage('Please open a Quantum file to explain errors');
        return;
    }

    const position = editor.selection.active;
    const errorContext = getErrorContext(editor.document, position);

    if (!errorContext) {
        vscode.window.showInformationMessage('No error found at current position');
        return;
    }

    // Show progress
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Analyzing error...',
        cancellable: false
    }, async () => {
        try {
            const aiProvider = getAIProvider();

            if (!aiProvider.isAvailable()) {
                // Fallback to built-in explanations
                const explanation = getBuiltInExplanation(errorContext);
                showExplanation(explanation, errorContext);
                return;
            }

            const prompt = getErrorExplanationPrompt(errorContext);
            const explanation = await aiProvider.complete(prompt);

            showExplanation(explanation, errorContext);
        } catch (error) {
            // Fallback to built-in explanations on error
            const explanation = getBuiltInExplanation(errorContext);
            showExplanation(explanation + '\n\n(AI explanation unavailable: ' + String(error) + ')', errorContext);
        }
    });
}

/**
 * Built-in error explanations for common errors
 */
function getBuiltInExplanation(errorContext: ErrorContext): string {
    const { errorMessage, tagContext } = errorContext;

    // Missing attribute errors
    if (errorMessage.includes('Missing required attribute')) {
        const attrMatch = errorMessage.match(/attribute\s+'(\w+)'/);
        const attr = attrMatch ? attrMatch[1] : 'unknown';

        const explanations: { [key: string]: string } = {
            name: `The **${tagContext}** tag requires a "name" attribute to identify it.

**How to fix:**
Add the name attribute: \`<${tagContext} name="myName">\`

**Example:**
\`\`\`xml
<q:component name="MyComponent">
    <!-- content -->
</q:component>
\`\`\``,
            var: `The **${tagContext}** tag requires a "var" attribute to specify the variable name.

**How to fix:**
Add the var attribute: \`<${tagContext} var="myVariable" value="...">\`

**Example:**
\`\`\`xml
<q:set var="counter" value="0"/>
\`\`\``,
            value: `The **${tagContext}** tag requires a "value" attribute.

**How to fix:**
Add the value attribute with the appropriate value.`,
            test: `The **${tagContext}** tag requires a "test" attribute for the condition.

**How to fix:**
Add a boolean expression: \`<${tagContext} test="condition">\`

**Example:**
\`\`\`xml
<q:if test="{count > 0}">
    <!-- content shown when count > 0 -->
</q:if>
\`\`\``
        };

        return explanations[attr] || `The **${tagContext}** tag is missing the required "${attr}" attribute.`;
    }

    // Unclosed tag errors
    if (errorMessage.includes('Unclosed tag') || errorMessage.includes('Expected closing tag')) {
        return `The **${tagContext}** tag is not properly closed.

**How to fix:**
Make sure every opening tag has a matching closing tag:
- Opening: \`<${tagContext}>\`
- Closing: \`</${tagContext}>\`

Or use self-closing syntax for tags without content:
\`<${tagContext} .../>\`

**Common mistakes:**
1. Missing closing tag entirely
2. Misspelled closing tag
3. Tags closed in wrong order (nesting issue)`;
    }

    // Unknown tag errors
    if (errorMessage.includes('Unknown tag') || errorMessage.includes('Invalid tag')) {
        return `The tag **${tagContext}** is not recognized.

**Possible causes:**
1. Typo in the tag name
2. Missing namespace prefix (should be \`q:\`)
3. Using a tag that doesn't exist in Quantum

**Common Quantum tags:**
- \`q:component\` - Define a component
- \`q:set\` - Set a variable
- \`q:if\` / \`q:else\` - Conditionals
- \`q:loop\` - Iteration
- \`q:function\` - Define a function
- \`q:output\` - Output a value
- \`q:query\` - Database query`;
    }

    // Invalid expression errors
    if (errorMessage.includes('Invalid expression') || errorMessage.includes('Expression error')) {
        return `There's an error in the expression syntax.

**Databinding syntax:**
Use curly braces for expressions: \`{variableName}\`

**Valid expressions:**
- Variable: \`{myVar}\`
- Property access: \`{user.name}\`
- Comparison: \`{count > 0}\`
- Arithmetic: \`{price * quantity}\`

**Common mistakes:**
1. Missing closing brace: \`{variable\` should be \`{variable}\`
2. Invalid characters in variable names
3. Unclosed string literals`;
    }

    // Generic explanation
    return `An error occurred in the **${tagContext}** tag.

**Error:** ${errorMessage}

**General tips:**
1. Check for typos in tag and attribute names
2. Ensure all tags are properly closed
3. Verify attribute values are correctly quoted
4. Check expression syntax within \`{...}\`

Refer to the Quantum documentation for more information about this tag.`;
}

/**
 * Register the explain error command
 */
export function registerExplainErrorCommand(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.explainError', explainError)
    );
}
