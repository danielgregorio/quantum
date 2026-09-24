/**
 * Document utility functions for the Quantum extension
 */

import * as vscode from 'vscode';

/**
 * Check if the document is a Quantum file
 */
export function isQuantumDocument(document: vscode.TextDocument): boolean {
    return document.languageId === 'quantum' || document.fileName.endsWith('.q');
}

/**
 * Get the word at a position (including namespaced tags like q:component)
 */
export function getWordAtPosition(document: vscode.TextDocument, position: vscode.Position): string | undefined {
    const range = document.getWordRangeAtPosition(position, /[a-zA-Z_:][\w:\-]*/);
    return range ? document.getText(range) : undefined;
}

/**
 * Get the full tag name at position (e.g., "q:component")
 */
export function getTagNameAtPosition(document: vscode.TextDocument, position: vscode.Position): string | undefined {
    const line = document.lineAt(position.line).text;
    const beforeCursor = line.substring(0, position.character);

    // Find the start of the tag
    const tagStartMatch = beforeCursor.match(/<([a-zA-Z_:][\w:\-]*)(?:\s|$)/g);
    if (!tagStartMatch) return undefined;

    // Get the last tag start before cursor
    const lastMatch = tagStartMatch[tagStartMatch.length - 1];
    return lastMatch.replace(/[<\s]/g, '');
}

/**
 * Get the current attribute context at position
 */
export interface AttributeContext {
    tagName: string;
    attributeName?: string;
    inValue: boolean;
    valuePrefix?: string;
    quoteChar?: string;
}

export function getAttributeContext(document: vscode.TextDocument, position: vscode.Position): AttributeContext | undefined {
    const text = document.getText();
    const offset = document.offsetAt(position);

    // Find the opening tag
    let tagStart = -1;
    for (let i = offset - 1; i >= 0; i--) {
        if (text[i] === '<' && text[i + 1] !== '/') {
            tagStart = i;
            break;
        }
        if (text[i] === '>') {
            return undefined; // Not inside a tag
        }
    }

    if (tagStart === -1) return undefined;

    const tagText = text.substring(tagStart, offset);

    // Check if tag is closed
    if (tagText.includes('>')) return undefined;

    // Extract tag name
    const tagNameMatch = tagText.match(/^<([a-zA-Z_:][\w:\-]*)/);
    if (!tagNameMatch) return undefined;

    const tagName = tagNameMatch[1];

    // Check if we're in an attribute value
    const lastQuote = Math.max(tagText.lastIndexOf('"'), tagText.lastIndexOf("'"));
    const lastEquals = tagText.lastIndexOf('=');

    if (lastQuote > lastEquals && lastQuote > 0) {
        const quoteChar = tagText[lastQuote];
        const afterQuote = tagText.substring(lastQuote + 1);

        // Check if quote is closed
        if (!afterQuote.includes(quoteChar)) {
            // We're inside a quoted value
            const beforeEquals = tagText.substring(0, lastEquals);
            const attrNameMatch = beforeEquals.match(/([a-zA-Z_:][a-zA-Z0-9_:\-]*)\s*$/);

            return {
                tagName,
                attributeName: attrNameMatch ? attrNameMatch[1] : undefined,
                inValue: true,
                valuePrefix: afterQuote,
                quoteChar
            };
        }
    }

    // We're in attribute name position
    const lastSpace = tagText.lastIndexOf(' ');
    const partialAttr = tagText.substring(lastSpace + 1).replace(/[=\s"']/g, '');

    return {
        tagName,
        attributeName: partialAttr || undefined,
        inValue: false
    };
}

/**
 * Extract variable names from databinding expressions in the document
 */
export function extractVariableNames(document: vscode.TextDocument): Set<string> {
    const variables = new Set<string>();
    const text = document.getText();

    // Find q:set definitions
    const setPattern = /<q:set\s+name="([^"]+)"/g;
    let match: RegExpExecArray | null;
    while ((match = setPattern.exec(text)) !== null) {
        variables.add(match[1]);
    }

    // Find q:param definitions
    const paramPattern = /<q:param\s+name="([^"]+)"/g;
    while ((match = paramPattern.exec(text)) !== null) {
        variables.add(match[1]);
    }

    // Find q:loop var definitions
    const loopVarPattern = /<q:loop[^>]+var="([^"]+)"/g;
    while ((match = loopVarPattern.exec(text)) !== null) {
        variables.add(match[1]);
    }

    // Find q:loop index definitions
    const loopIndexPattern = /<q:loop[^>]+index="([^"]+)"/g;
    while ((match = loopIndexPattern.exec(text)) !== null) {
        variables.add(match[1]);
    }

    // Find q:query name definitions
    const queryPattern = /<q:query[^>]+name="([^"]+)"/g;
    while ((match = queryPattern.exec(text)) !== null) {
        variables.add(match[1]);
    }

    // Find ui:list as definitions
    const listPattern = /<ui:list[^>]+as="([^"]+)"/g;
    while ((match = listPattern.exec(text)) !== null) {
        variables.add(match[1]);
    }

    return variables;
}

/**
 * Extract function names from the document
 */
export function extractFunctionNames(document: vscode.TextDocument): Set<string> {
    const functions = new Set<string>();
    const text = document.getText();

    const funcPattern = /<q:function\s+name="([^"]+)"/g;
    let match: RegExpExecArray | null;
    while ((match = funcPattern.exec(text)) !== null) {
        functions.add(match[1]);
    }

    return functions;
}

/**
 * Extract imported component names from the document
 */
export function extractImportedComponents(document: vscode.TextDocument): Map<string, { from?: string; component: string }> {
    const imports = new Map<string, { from?: string; component: string }>();
    const text = document.getText();

    const importPattern = /<q:import\s+component="([^"]+)"(?:\s+from="([^"]+)")?(?:\s+as="([^"]+)")?/g;
    let match: RegExpExecArray | null;
    while ((match = importPattern.exec(text)) !== null) {
        const component = match[1];
        const from = match[2];
        const alias = match[3] || component;
        imports.set(alias, { from, component });
    }

    return imports;
}

/**
 * Find the definition location of a symbol
 */
export function findDefinition(document: vscode.TextDocument, symbolName: string): vscode.Location | undefined {
    const text = document.getText();

    // Check for function definition
    const funcPattern = new RegExp(`<q:function\\s+name="${symbolName}"`, 'g');
    let match = funcPattern.exec(text);
    if (match) {
        const pos = document.positionAt(match.index);
        return new vscode.Location(document.uri, pos);
    }

    // Check for component definition
    const compPattern = new RegExp(`<q:component\\s+name="${symbolName}"`, 'g');
    match = compPattern.exec(text);
    if (match) {
        const pos = document.positionAt(match.index);
        return new vscode.Location(document.uri, pos);
    }

    // Check for variable definition (q:set)
    const setPattern = new RegExp(`<q:set\\s+name="${symbolName}"`, 'g');
    match = setPattern.exec(text);
    if (match) {
        const pos = document.positionAt(match.index);
        return new vscode.Location(document.uri, pos);
    }

    // Check for query definition
    const queryPattern = new RegExp(`<q:query\\s+[^>]*name="${symbolName}"`, 'g');
    match = queryPattern.exec(text);
    if (match) {
        const pos = document.positionAt(match.index);
        return new vscode.Location(document.uri, pos);
    }

    return undefined;
}

/**
 * Get the range of a tag starting at a position
 */
export function getTagRange(document: vscode.TextDocument, startPosition: vscode.Position): vscode.Range | undefined {
    const text = document.getText();
    const startOffset = document.offsetAt(startPosition);

    // Check if we're at a tag start
    if (text[startOffset] !== '<') return undefined;

    // Find the closing >
    let endOffset = text.indexOf('>', startOffset);
    if (endOffset === -1) return undefined;

    endOffset++; // Include the >

    return new vscode.Range(startPosition, document.positionAt(endOffset));
}

/**
 * Format databinding expression for display
 */
export function formatExpression(expression: string): string {
    return expression.trim().replace(/\s+/g, ' ');
}

/**
 * Check if a string is a valid identifier
 */
export function isValidIdentifier(name: string): boolean {
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

/**
 * Get the indentation of a line
 */
export function getLineIndentation(document: vscode.TextDocument, line: number): string {
    const lineText = document.lineAt(line).text;
    const match = lineText.match(/^(\s*)/);
    return match ? match[1] : '';
}

/**
 * Create a snippet string for tag completion
 */
export function createTagSnippet(tagName: string, requiredAttrs: string[], selfClosing: boolean): string {
    let snippet = `<${tagName}`;

    requiredAttrs.forEach((attr, index) => {
        snippet += ` ${attr}="\${${index + 1}:}"`;
    });

    if (selfClosing) {
        snippet += ' />$0';
    } else {
        snippet += `>$0</${tagName}>`;
    }

    return snippet;
}
