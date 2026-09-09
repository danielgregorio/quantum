/**
 * Quantum Documentation Lookup Command
 *
 * Provides documentation lookup for Quantum tags and attributes:
 * - Command: "Quantum: Lookup Documentation"
 * - Shows documentation in a panel
 * - Search docs for current tag/attribute
 */

import * as vscode from 'vscode';
import { getAIProvider, isAIConfigured } from '../ai/aiProvider';
import { getDocumentationPrompt } from '../ai/prompts';

/**
 * Built-in documentation for Quantum tags
 */
const QUANTUM_DOCS: { [key: string]: TagDocumentation } = {
    'q:component': {
        name: 'q:component',
        purpose: 'Defines a reusable Quantum component. Components encapsulate logic, state, and UI.',
        requiredAttributes: [
            { name: 'name', description: 'Unique name for the component (PascalCase recommended)' }
        ],
        optionalAttributes: [
            { name: 'extends', description: 'Parent component to inherit from' }
        ],
        example: `<q:component name="UserCard">
    <q:set var="name" value=""/>

    <div class="card">
        <h2>{name}</h2>
    </div>
</q:component>`,
        commonPatterns: [
            'Define variables at the top of the component',
            'Group related functions together',
            'Keep UI at the bottom'
        ]
    },
    'q:set': {
        name: 'q:set',
        purpose: 'Sets a variable in the current scope. Variables can hold strings, numbers, arrays, or objects.',
        requiredAttributes: [
            { name: 'var', description: 'Name of the variable to set' },
            { name: 'value', description: 'Value to assign to the variable' }
        ],
        optionalAttributes: [
            { name: 'scope', description: 'Variable scope: "local" (default), "session", or "application"' }
        ],
        example: `<q:set var="counter" value="0"/>
<q:set var="name" value="John Doe"/>
<q:set var="items" value="[]"/>`,
        commonPatterns: [
            'Use descriptive variable names',
            'Initialize variables before use',
            'Use scope="session" for user-specific data'
        ]
    },
    'q:output': {
        name: 'q:output',
        purpose: 'Outputs a value to the rendered HTML. Automatically escapes HTML by default.',
        requiredAttributes: [
            { name: 'value', description: 'Expression or variable to output' }
        ],
        optionalAttributes: [
            { name: 'escape', description: 'Whether to HTML-escape the output (default: true)' },
            { name: 'format', description: 'Format string for numbers/dates' }
        ],
        example: `<q:output value="{username}"/>
<q:output value="{price}" format="currency"/>
<q:output value="{htmlContent}" escape="false"/>`,
        commonPatterns: [
            'Use databinding syntax {var} in HTML attributes instead',
            'Set escape="false" only for trusted HTML content',
            'Use format for consistent number/date display'
        ]
    },
    'q:if': {
        name: 'q:if',
        purpose: 'Conditionally renders content based on a boolean expression.',
        requiredAttributes: [
            { name: 'test', description: 'Boolean expression to evaluate' }
        ],
        optionalAttributes: [],
        example: `<q:if test="{isLoggedIn}">
    <p>Welcome, {username}!</p>
</q:if>

<q:if test="{count > 0}">
    <p>You have {count} items.</p>
<q:else>
    <p>No items found.</p>
</q:else>
</q:if>`,
        commonPatterns: [
            'Use q:else for alternate content',
            'Use q:elseif for multiple conditions',
            'Keep conditions simple; use functions for complex logic'
        ]
    },
    'q:else': {
        name: 'q:else',
        purpose: 'Provides alternate content when the preceding q:if condition is false.',
        requiredAttributes: [],
        optionalAttributes: [],
        example: `<q:if test="{hasData}">
    <DataView data="{data}"/>
<q:else>
    <p>No data available.</p>
</q:else>
</q:if>`,
        commonPatterns: [
            'Must follow a q:if or q:elseif tag',
            'Only one q:else per q:if block'
        ]
    },
    'q:elseif': {
        name: 'q:elseif',
        purpose: 'Provides an additional condition to check when the preceding condition is false.',
        requiredAttributes: [
            { name: 'test', description: 'Boolean expression to evaluate' }
        ],
        optionalAttributes: [],
        example: `<q:if test="{status == 'success'}">
    <span class="success">Success!</span>
<q:elseif test="{status == 'warning'}">
    <span class="warning">Warning</span>
<q:else>
    <span class="error">Error</span>
</q:else>
</q:if>`,
        commonPatterns: [
            'Must follow a q:if or another q:elseif',
            'Can have multiple q:elseif tags',
            'Consider using a lookup table for many conditions'
        ]
    },
    'q:loop': {
        name: 'q:loop',
        purpose: 'Iterates over an array or a numeric range.',
        requiredAttributes: [],
        optionalAttributes: [
            { name: 'array', description: 'Array to iterate over' },
            { name: 'item', description: 'Variable name for current item' },
            { name: 'index', description: 'Variable name for current index' },
            { name: 'from', description: 'Start number for numeric loop' },
            { name: 'to', description: 'End number for numeric loop' },
            { name: 'step', description: 'Increment value (default: 1)' }
        ],
        example: `<!-- Array loop -->
<q:loop array="{users}" item="user" index="i">
    <div>{i + 1}. {user.name}</div>
</q:loop>

<!-- Numeric loop -->
<q:loop from="1" to="10" index="num">
    <span>{num}</span>
</q:loop>`,
        commonPatterns: [
            'Use array + item for collections',
            'Use from + to + index for numeric ranges',
            'Access index for numbering or alternating styles'
        ]
    },
    'q:function': {
        name: 'q:function',
        purpose: 'Defines a reusable function within the component.',
        requiredAttributes: [
            { name: 'name', description: 'Function name (camelCase recommended)' }
        ],
        optionalAttributes: [
            { name: 'params', description: 'Comma-separated list of parameter names' },
            { name: 'returns', description: 'Description of return value' }
        ],
        example: `<q:function name="calculateTotal" params="items, taxRate">
    <q:set var="subtotal" value="0"/>
    <q:loop array="{items}" item="item">
        <q:set var="subtotal" value="{subtotal + item.price}"/>
    </q:loop>
    <q:return value="{subtotal * (1 + taxRate)}"/>
</q:function>

<!-- Usage -->
<q:set var="total" value="{calculateTotal(cartItems, 0.08)}"/>`,
        commonPatterns: [
            'Keep functions focused and single-purpose',
            'Use descriptive parameter names',
            'Document complex functions with comments'
        ]
    },
    'q:query': {
        name: 'q:query',
        purpose: 'Executes a database query and stores results in a variable.',
        requiredAttributes: [
            { name: 'name', description: 'Variable name to store results' },
            { name: 'datasource', description: 'Database connection name' }
        ],
        optionalAttributes: [
            { name: 'maxrows', description: 'Maximum number of rows to return' },
            { name: 'timeout', description: 'Query timeout in seconds' }
        ],
        example: `<q:query name="users" datasource="mainDB">
    SELECT id, name, email
    FROM users
    WHERE active = 1
    ORDER BY name
</q:query>

<q:loop array="{users}" item="user">
    <div>{user.name} ({user.email})</div>
</q:loop>`,
        commonPatterns: [
            'Use parameterized queries for user input',
            'Set appropriate maxrows for pagination',
            'Handle empty results gracefully'
        ]
    },
    'q:include': {
        name: 'q:include',
        purpose: 'Includes another Quantum file or component.',
        requiredAttributes: [
            { name: 'src', description: 'Path to the file to include' }
        ],
        optionalAttributes: [
            { name: 'cache', description: 'Whether to cache the included content' }
        ],
        example: `<q:include src="./components/header.q"/>
<q:include src="./partials/navigation.q"/>`,
        commonPatterns: [
            'Use relative paths from current file',
            'Organize components in a components/ directory',
            'Use for shared layouts and partials'
        ]
    },
    'q:action': {
        name: 'q:action',
        purpose: 'Handles form submissions and user actions.',
        requiredAttributes: [
            { name: 'name', description: 'Unique action identifier' }
        ],
        optionalAttributes: [
            { name: 'method', description: 'HTTP method: GET or POST (default: POST)' },
            { name: 'validate', description: 'Whether to validate form data' }
        ],
        example: `<q:action name="submitForm">
    <q:set var="name" value="{form.name}"/>
    <q:query name="insert" datasource="db">
        INSERT INTO users (name) VALUES ('{name}')
    </q:query>
    <q:redirect url="/success"/>
</q:action>

<form action="?action=submitForm" method="post">
    <input name="name" type="text"/>
    <button type="submit">Submit</button>
</form>`,
        commonPatterns: [
            'Validate user input before processing',
            'Use q:redirect after successful actions',
            'Handle errors with q:try/q:catch'
        ]
    }
};

interface TagDocumentation {
    name: string;
    purpose: string;
    requiredAttributes: { name: string; description: string }[];
    optionalAttributes: { name: string; description: string }[];
    example: string;
    commonPatterns: string[];
}

let documentationPanel: vscode.WebviewPanel | undefined;

/**
 * Get tag at cursor position
 */
function getTagAtCursor(document: vscode.TextDocument, position: vscode.Position): {
    tagName: string;
    attributes: string[];
    fullTag: string;
} | undefined {
    const lineText = document.lineAt(position.line).text;

    // Find tag at cursor
    const tagRegex = /<(q:[\w-]+|[\w-]+)([^>]*)>/g;
    let match;

    while ((match = tagRegex.exec(lineText)) !== null) {
        const start = match.index;
        const end = match.index + match[0].length;

        if (position.character >= start && position.character <= end) {
            const tagName = match[1];
            const attrStr = match[2];

            // Parse attributes
            const attributes: string[] = [];
            const attrRegex = /(\w+)=/g;
            let attrMatch;
            while ((attrMatch = attrRegex.exec(attrStr)) !== null) {
                attributes.push(attrMatch[1]);
            }

            return {
                tagName,
                attributes,
                fullTag: match[0]
            };
        }
    }

    return undefined;
}

/**
 * Show documentation in a panel
 */
function showDocumentation(tagName: string, docs: TagDocumentation | string): void {
    if (!documentationPanel) {
        documentationPanel = vscode.window.createWebviewPanel(
            'quantumDocumentation',
            'Quantum Documentation',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        documentationPanel.onDidDispose(() => {
            documentationPanel = undefined;
        });
    }

    documentationPanel.title = `Docs: ${tagName}`;

    if (typeof docs === 'string') {
        // AI-generated documentation (markdown)
        documentationPanel.webview.html = getMarkdownHtml(tagName, docs);
    } else {
        // Built-in documentation
        documentationPanel.webview.html = getDocumentationHtml(docs);
    }

    documentationPanel.reveal();
}

/**
 * Generate HTML for built-in documentation
 */
function getDocumentationHtml(docs: TagDocumentation): string {
    const requiredAttrs = docs.requiredAttributes
        .map(a => `<li><code>${a.name}</code> - ${a.description} <span class="required">(required)</span></li>`)
        .join('\n');

    const optionalAttrs = docs.optionalAttributes
        .map(a => `<li><code>${a.name}</code> - ${a.description}</li>`)
        .join('\n');

    const patterns = docs.commonPatterns
        .map(p => `<li>${p}</li>`)
        .join('\n');

    const escapedExample = docs.example
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${docs.name} Documentation</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            line-height: 1.6;
        }
        h1 {
            color: var(--vscode-textLink-foreground);
            border-bottom: 2px solid var(--vscode-textLink-foreground);
            padding-bottom: 8px;
        }
        h2 {
            margin-top: 24px;
            color: var(--vscode-foreground);
        }
        .purpose {
            font-size: 1.1em;
            margin-bottom: 20px;
        }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: var(--vscode-editor-font-family);
        }
        pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 16px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
        }
        ul {
            padding-left: 20px;
        }
        li {
            margin: 8px 0;
        }
        .required {
            color: var(--vscode-errorForeground);
            font-size: 0.85em;
        }
        .section {
            margin: 20px 0;
            padding: 16px;
            background: var(--vscode-textBlockQuote-background);
            border-left: 4px solid var(--vscode-textBlockQuote-border);
            border-radius: 0 4px 4px 0;
        }
    </style>
</head>
<body>
    <h1>&lt;${docs.name}&gt;</h1>
    <p class="purpose">${docs.purpose}</p>

    ${docs.requiredAttributes.length > 0 || docs.optionalAttributes.length > 0 ? `
    <h2>Attributes</h2>
    <ul>
        ${requiredAttrs}
        ${optionalAttrs}
    </ul>
    ` : ''}

    <h2>Example</h2>
    <pre>${escapedExample}</pre>

    ${docs.commonPatterns.length > 0 ? `
    <div class="section">
        <h2>Common Patterns</h2>
        <ul>
            ${patterns}
        </ul>
    </div>
    ` : ''}
</body>
</html>`;
}

/**
 * Generate HTML for markdown documentation
 */
function getMarkdownHtml(tagName: string, markdown: string): string {
    // Simple markdown to HTML conversion
    const html = markdown
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)+/g, '<ul>$&</ul>');

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${tagName} Documentation</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            line-height: 1.6;
        }
        h1, h2, h3 {
            color: var(--vscode-textLink-foreground);
        }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: var(--vscode-editor-font-family);
        }
        pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 16px;
            border-radius: 4px;
            overflow-x: auto;
        }
        pre code {
            padding: 0;
        }
        ul {
            padding-left: 20px;
        }
        li {
            margin: 8px 0;
        }
        .ai-notice {
            background: var(--vscode-inputValidation-infoBackground);
            border: 1px solid var(--vscode-inputValidation-infoBorder);
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 16px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="ai-notice">AI-generated documentation</div>
    <h1>&lt;${tagName}&gt;</h1>
    <p>${html}</p>
</body>
</html>`;
}

/**
 * Main command: Lookup Documentation
 */
export async function lookupDocumentation(): Promise<void> {
    const editor = vscode.window.activeTextEditor;

    if (!editor || editor.document.languageId !== 'quantum') {
        // Show tag picker
        const tags = Object.keys(QUANTUM_DOCS);
        const selected = await vscode.window.showQuickPick(tags, {
            placeHolder: 'Select a Quantum tag to view documentation'
        });

        if (selected && QUANTUM_DOCS[selected]) {
            showDocumentation(selected, QUANTUM_DOCS[selected]);
        }
        return;
    }

    // Get tag at cursor
    const tagInfo = getTagAtCursor(editor.document, editor.selection.active);

    if (!tagInfo) {
        // Show tag picker
        const tags = Object.keys(QUANTUM_DOCS);
        const selected = await vscode.window.showQuickPick(tags, {
            placeHolder: 'Select a Quantum tag to view documentation'
        });

        if (selected && QUANTUM_DOCS[selected]) {
            showDocumentation(selected, QUANTUM_DOCS[selected]);
        }
        return;
    }

    // Check if we have built-in docs
    if (QUANTUM_DOCS[tagInfo.tagName]) {
        showDocumentation(tagInfo.tagName, QUANTUM_DOCS[tagInfo.tagName]);
        return;
    }

    // Try AI for unknown tags
    if (isAIConfigured()) {
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `Looking up documentation for ${tagInfo.tagName}...`,
            cancellable: false
        }, async () => {
            try {
                const aiProvider = getAIProvider();
                const prompt = getDocumentationPrompt({
                    tagName: tagInfo.tagName,
                    attributes: tagInfo.attributes,
                    currentCode: tagInfo.fullTag
                });

                const docs = await aiProvider.complete(prompt);
                showDocumentation(tagInfo.tagName, docs);
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to get documentation: ${error}`);
            }
        });
    } else {
        vscode.window.showInformationMessage(
            `No documentation found for ${tagInfo.tagName}. Configure AI to get documentation for custom tags.`
        );
    }
}

/**
 * Register the documentation lookup command
 */
export function registerDocumentationLookup(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.lookupDocumentation', lookupDocumentation)
    );

    // Also register hover provider for documentation
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { language: 'quantum', scheme: 'file' },
            {
                provideHover(document, position, token) {
                    const tagInfo = getTagAtCursor(document, position);
                    if (!tagInfo || !QUANTUM_DOCS[tagInfo.tagName]) {
                        return undefined;
                    }

                    const docs = QUANTUM_DOCS[tagInfo.tagName];
                    const markdown = new vscode.MarkdownString();
                    markdown.appendMarkdown(`**${docs.name}**\n\n`);
                    markdown.appendMarkdown(`${docs.purpose}\n\n`);

                    if (docs.requiredAttributes.length > 0) {
                        markdown.appendMarkdown('**Required:** ');
                        markdown.appendMarkdown(docs.requiredAttributes.map(a => `\`${a.name}\``).join(', '));
                        markdown.appendMarkdown('\n\n');
                    }

                    markdown.appendMarkdown(`[View full documentation](command:quantum.lookupDocumentation)`);
                    markdown.isTrusted = true;

                    return new vscode.Hover(markdown);
                }
            }
        )
    );
}
