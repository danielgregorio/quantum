/**
 * Hover Provider for Quantum Language
 *
 * Provides documentation when hovering over:
 * - Tag names
 * - Attribute names
 * - Databinding expressions
 */

import * as vscode from 'vscode';
import {
    getTagSchema,
    getAttributeSchema,
    TagSchema,
    AttributeSchema
} from '../language/quantumSchema';
import { createParser } from '../language/quantumParser';
import {
    extractVariableNames,
    extractFunctionNames,
    findDefinition
} from '../utils/documentUtils';

export class QuantumHoverProvider implements vscode.HoverProvider {

    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Hover> {

        const parser = createParser(document);
        const cursorContext = parser.getCursorContext(position);

        // Get the word at cursor position
        const wordRange = document.getWordRangeAtPosition(position, /[a-zA-Z_:][\w:\-]*/);
        if (!wordRange) return undefined;

        const word = document.getText(wordRange);

        // Check if hovering over a tag name
        if (cursorContext.inTag && !cursorContext.inAttributeValue) {
            // Check if this is the tag name
            if (word === cursorContext.tagName || word.includes(':')) {
                const tag = getTagSchema(word);
                if (tag) {
                    return new vscode.Hover(this.formatTagHover(tag), wordRange);
                }
            }

            // Check if this is an attribute name
            if (cursorContext.tagName) {
                const attr = getAttributeSchema(cursorContext.tagName, word);
                if (attr) {
                    return new vscode.Hover(
                        this.formatAttributeHover(cursorContext.tagName, attr),
                        wordRange
                    );
                }
            }
        }

        // Check if hovering in a databinding expression
        if (cursorContext.inDataBinding || this.isInDataBinding(document, position)) {
            return this.provideDataBindingHover(document, word, wordRange);
        }

        // Check if hovering over a tag in general
        const line = document.lineAt(position.line).text;
        const tagMatch = line.match(/<\/?([a-zA-Z_:][\w:\-]*)/);
        if (tagMatch && line.indexOf(tagMatch[0]) <= position.character) {
            const tagName = tagMatch[1];
            if (word === tagName || tagName.endsWith(word)) {
                const tag = getTagSchema(tagName);
                if (tag) {
                    return new vscode.Hover(this.formatTagHover(tag), wordRange);
                }
            }
        }

        return undefined;
    }

    /**
     * Check if position is inside a databinding expression
     */
    private isInDataBinding(document: vscode.TextDocument, position: vscode.Position): boolean {
        const line = document.lineAt(position.line).text;
        const beforeCursor = line.substring(0, position.character);
        const afterCursor = line.substring(position.character);

        const lastOpen = beforeCursor.lastIndexOf('{');
        const lastClose = beforeCursor.lastIndexOf('}');

        if (lastOpen > lastClose) {
            // Check if there's a closing brace after cursor
            return afterCursor.includes('}');
        }

        return false;
    }

    /**
     * Provide hover for databinding expressions
     */
    private provideDataBindingHover(
        document: vscode.TextDocument,
        word: string,
        wordRange: vscode.Range
    ): vscode.Hover | undefined {

        const parser = createParser(document);
        const parseResult = parser.parse();

        // Check if it's a variable
        const variable = parseResult.variables.get(word);
        if (variable) {
            const content = new vscode.MarkdownString();
            content.appendCodeblock(`(variable) ${word}: ${variable.type || 'any'}`, 'typescript');
            if (variable.scope) {
                content.appendMarkdown(`\n\n**Scope:** \`${variable.scope}\``);
            }
            return new vscode.Hover(content, wordRange);
        }

        // Check if it's a function
        const func = parseResult.functions.get(word);
        if (func) {
            const params = func.params.join(', ');
            const returnType = func.returnType || 'any';
            const content = new vscode.MarkdownString();
            content.appendCodeblock(`(function) ${word}(${params}): ${returnType}`, 'typescript');
            return new vscode.Hover(content, wordRange);
        }

        // Check if it's a query
        const text = document.getText();
        const queryMatch = text.match(new RegExp(`<q:query[^>]*name="${word}"[^>]*>`));
        if (queryMatch) {
            const content = new vscode.MarkdownString();
            content.appendCodeblock(`(query) ${word}: QueryResult[]`, 'typescript');
            content.appendMarkdown('\n\nDatabase query result set. Iterate with `<q:loop query="' + word + '">`.');
            return new vscode.Hover(content, wordRange);
        }

        // Check if it's an imported component
        const imports = parseResult.imports.get(word);
        if (imports) {
            const content = new vscode.MarkdownString();
            content.appendCodeblock(`(component) ${word}`, 'typescript');
            if (imports.from) {
                content.appendMarkdown(`\n\nImported from \`${imports.from}\``);
            }
            return new vscode.Hover(content, wordRange);
        }

        return undefined;
    }

    /**
     * Format hover content for a tag
     */
    private formatTagHover(tag: TagSchema): vscode.MarkdownString {
        const content = new vscode.MarkdownString();

        // Header
        content.appendMarkdown(`## \`<${tag.namespace}:${tag.name}>\`\n\n`);

        // Description
        content.appendMarkdown(tag.description + '\n\n');

        // Category
        if (tag.category) {
            content.appendMarkdown(`**Category:** ${tag.category}\n\n`);
        }

        // Attributes table
        if (tag.attributes.length > 0) {
            content.appendMarkdown('### Attributes\n\n');

            // Required attributes first
            const required = tag.attributes.filter(a => a.required);
            const optional = tag.attributes.filter(a => !a.required);

            if (required.length > 0) {
                content.appendMarkdown('**Required:**\n');
                for (const attr of required) {
                    content.appendMarkdown(`- \`${attr.name}\` - ${attr.description}\n`);
                }
                content.appendMarkdown('\n');
            }

            if (optional.length > 0) {
                content.appendMarkdown('**Optional:**\n');
                // Show first 5 optional attributes
                for (const attr of optional.slice(0, 5)) {
                    let attrDoc = `- \`${attr.name}\``;
                    if (attr.type === 'enum' && attr.values) {
                        attrDoc += ` (${attr.values.slice(0, 3).join(' | ')}${attr.values.length > 3 ? ' | ...' : ''})`;
                    } else if (attr.type) {
                        attrDoc += ` (${attr.type})`;
                    }
                    attrDoc += ` - ${attr.description}\n`;
                    content.appendMarkdown(attrDoc);
                }
                if (optional.length > 5) {
                    content.appendMarkdown(`\n*...and ${optional.length - 5} more*\n`);
                }
            }
        }

        // Self-closing note
        if (tag.selfClosing) {
            content.appendMarkdown('\n*Self-closing tag*');
        }

        return content;
    }

    /**
     * Format hover content for an attribute
     */
    private formatAttributeHover(tagName: string, attr: AttributeSchema): vscode.MarkdownString {
        const content = new vscode.MarkdownString();

        // Header
        content.appendMarkdown(`## \`${attr.name}\`\n\n`);
        content.appendMarkdown(`Attribute of \`<${tagName}>\`\n\n`);

        // Description
        content.appendMarkdown(attr.description + '\n\n');

        // Type
        if (attr.type) {
            content.appendMarkdown(`**Type:** \`${attr.type}\`\n\n`);
        }

        // Values for enum
        if (attr.type === 'enum' && attr.values) {
            content.appendMarkdown('**Allowed values:**\n');
            for (const value of attr.values) {
                content.appendMarkdown(`- \`${value}\`\n`);
            }
            content.appendMarkdown('\n');
        }

        // Default value
        if (attr.default) {
            content.appendMarkdown(`**Default:** \`${attr.default}\`\n\n`);
        }

        // Required
        if (attr.required) {
            content.appendMarkdown('*Required attribute*');
        }

        return content;
    }
}

/**
 * Register the hover provider
 */
export function registerHoverProvider(context: vscode.ExtensionContext): void {
    const provider = new QuantumHoverProvider();

    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { language: 'quantum', scheme: 'file' },
            provider
        )
    );
}
