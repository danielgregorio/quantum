/**
 * Completion Provider for Quantum Language
 *
 * Provides IntelliSense/autocomplete for:
 * - Tag names (q:*, ui:*, etc.)
 * - Attribute names based on tag
 * - Attribute values (enums, booleans)
 * - Variable references in databinding expressions
 */

import * as vscode from 'vscode';
import {
    allTags,
    getTagSchema,
    getAttributeNames,
    getAttributeSchema,
    TagSchema,
    AttributeSchema
} from '../language/quantumSchema';
import { createParser } from '../language/quantumParser';
import {
    getAttributeContext,
    extractVariableNames,
    extractFunctionNames,
    extractImportedComponents
} from '../utils/documentUtils';

export class QuantumCompletionProvider implements vscode.CompletionItemProvider {

    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): vscode.ProviderResult<vscode.CompletionItem[] | vscode.CompletionList> {

        const parser = createParser(document);
        const cursorContext = parser.getCursorContext(position);

        // Check if we're in a databinding expression
        if (cursorContext.inDataBinding) {
            return this.provideDataBindingCompletions(document, cursorContext);
        }

        // Check if we're inside a tag
        if (cursorContext.inTag) {
            if (cursorContext.inAttributeValue) {
                // Provide attribute value completions
                return this.provideAttributeValueCompletions(
                    document,
                    cursorContext.tagName || '',
                    cursorContext.attributeName || ''
                );
            } else if (cursorContext.inAttribute) {
                // Provide attribute name completions
                return this.provideAttributeCompletions(cursorContext.tagName || '');
            }
        }

        // Check if we're starting a new tag
        const line = document.lineAt(position.line).text;
        const beforeCursor = line.substring(0, position.character);

        if (beforeCursor.endsWith('<')) {
            return this.provideTagCompletions(document);
        }

        if (beforeCursor.endsWith('</')) {
            return this.provideClosingTagCompletions(document, position);
        }

        return [];
    }

    /**
     * Provide tag name completions
     */
    private provideTagCompletions(document: vscode.TextDocument): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];

        // Add all Quantum and UI tags
        for (const tag of allTags) {
            const fullName = `${tag.namespace}:${tag.name}`;
            const item = new vscode.CompletionItem(fullName, vscode.CompletionItemKind.Class);
            item.detail = `(${tag.category || tag.namespace})`;
            item.documentation = new vscode.MarkdownString(tag.description);

            // Create snippet with required attributes
            const requiredAttrs = tag.attributes.filter(a => a.required);
            let snippet = `${fullName}`;

            requiredAttrs.forEach((attr, index) => {
                snippet += ` ${attr.name}="\${${index + 1}:}"`;
            });

            if (tag.selfClosing) {
                snippet += ' />$0';
            } else {
                snippet += `>\n\t$0\n</${fullName}>`;
            }

            item.insertText = new vscode.SnippetString(snippet);

            // Sort by namespace then name
            item.sortText = `${tag.namespace}_${tag.name}`;

            items.push(item);
        }

        // Add imported components
        const imports = extractImportedComponents(document);
        for (const [alias, info] of imports) {
            const item = new vscode.CompletionItem(alias, vscode.CompletionItemKind.Class);
            item.detail = `(imported component)`;
            item.documentation = new vscode.MarkdownString(
                info.from ? `Imported from \`${info.from}\`` : `Imported component`
            );
            item.insertText = new vscode.SnippetString(`${alias} $0 />`);
            item.sortText = `0_${alias}`; // Sort imports first
            items.push(item);
        }

        return items;
    }

    /**
     * Provide closing tag completions
     */
    private provideClosingTagCompletions(
        document: vscode.TextDocument,
        position: vscode.Position
    ): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];
        const text = document.getText(new vscode.Range(new vscode.Position(0, 0), position));

        // Find unclosed tags
        const openTags: string[] = [];
        const tagPattern = /<(\/?)([a-zA-Z_:][\w:\-]*)[^>]*?(\/?)\s*>/g;
        let match: RegExpExecArray | null;

        while ((match = tagPattern.exec(text)) !== null) {
            const isClosing = match[1] === '/';
            const tagName = match[2];
            const isSelfClosing = match[3] === '/';

            if (isClosing) {
                // Remove the matching opening tag from stack
                const lastIndex = openTags.lastIndexOf(tagName);
                if (lastIndex !== -1) {
                    openTags.splice(lastIndex, 1);
                }
            } else if (!isSelfClosing) {
                openTags.push(tagName);
            }
        }

        // Suggest closing tags in reverse order (most recent first)
        for (let i = openTags.length - 1; i >= 0; i--) {
            const tagName = openTags[i];
            const item = new vscode.CompletionItem(tagName, vscode.CompletionItemKind.Class);
            item.detail = 'Close tag';
            item.insertText = `${tagName}>`;
            item.sortText = String(openTags.length - i).padStart(3, '0');
            items.push(item);
        }

        return items;
    }

    /**
     * Provide attribute name completions for a tag
     */
    private provideAttributeCompletions(tagName: string): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];
        const tag = getTagSchema(tagName);

        if (!tag) return items;

        for (const attr of tag.attributes) {
            const item = new vscode.CompletionItem(attr.name, vscode.CompletionItemKind.Property);
            item.detail = attr.required ? '(required)' : '(optional)';
            item.documentation = new vscode.MarkdownString(this.formatAttributeDoc(attr));

            // Create snippet based on attribute type
            if (attr.type === 'boolean') {
                item.insertText = new vscode.SnippetString(`${attr.name}="\${1|true,false|}"$0`);
            } else if (attr.type === 'enum' && attr.values) {
                const values = attr.values.join(',');
                item.insertText = new vscode.SnippetString(`${attr.name}="\${1|${values}|}"$0`);
            } else {
                item.insertText = new vscode.SnippetString(`${attr.name}="$1"$0`);
            }

            // Sort required attributes first
            item.sortText = attr.required ? `0_${attr.name}` : `1_${attr.name}`;

            items.push(item);
        }

        return items;
    }

    /**
     * Provide attribute value completions
     */
    private provideAttributeValueCompletions(
        document: vscode.TextDocument,
        tagName: string,
        attrName: string
    ): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];
        const attr = getAttributeSchema(tagName, attrName);

        if (attr) {
            if (attr.type === 'boolean') {
                items.push(this.createValueItem('true', 'Boolean true'));
                items.push(this.createValueItem('false', 'Boolean false'));
            } else if (attr.type === 'enum' && attr.values) {
                for (const value of attr.values) {
                    items.push(this.createValueItem(value, `Option: ${value}`));
                }
            } else if (attr.type === 'expression') {
                // Suggest databinding wrapper
                const item = new vscode.CompletionItem('{expression}', vscode.CompletionItemKind.Snippet);
                item.insertText = new vscode.SnippetString('{$1}');
                item.detail = 'Databinding expression';
                items.push(item);

                // Suggest known variables
                const variables = extractVariableNames(document);
                for (const varName of variables) {
                    const item = new vscode.CompletionItem(`{${varName}}`, vscode.CompletionItemKind.Variable);
                    item.insertText = `{${varName}}`;
                    item.detail = 'Variable reference';
                    items.push(item);
                }
            }
        }

        // For handler attributes (on-click, on-submit, etc.), suggest functions
        if (attrName.startsWith('on-') || attrName === 'on_submit' || attrName === 'on_change') {
            const functions = extractFunctionNames(document);
            for (const funcName of functions) {
                const item = new vscode.CompletionItem(funcName, vscode.CompletionItemKind.Function);
                item.detail = 'Function reference';
                items.push(item);
            }
        }

        // For 'bind' attributes, suggest variables
        if (attrName === 'bind') {
            const variables = extractVariableNames(document);
            for (const varName of variables) {
                const item = new vscode.CompletionItem(varName, vscode.CompletionItemKind.Variable);
                item.detail = 'Variable binding';
                items.push(item);
            }
        }

        return items;
    }

    /**
     * Provide completions inside databinding expressions
     */
    private provideDataBindingCompletions(
        document: vscode.TextDocument,
        context: { expressionPrefix?: string }
    ): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];

        // Add variables
        const variables = extractVariableNames(document);
        for (const varName of variables) {
            const item = new vscode.CompletionItem(varName, vscode.CompletionItemKind.Variable);
            item.detail = 'Variable';
            items.push(item);
        }

        // Add functions
        const functions = extractFunctionNames(document);
        for (const funcName of functions) {
            const item = new vscode.CompletionItem(funcName, vscode.CompletionItemKind.Function);
            item.detail = 'Function';
            item.insertText = new vscode.SnippetString(`${funcName}($1)`);
            items.push(item);
        }

        // Add common expression helpers
        const helpers = [
            { name: 'length', desc: 'Array/string length', snippet: 'length' },
            { name: 'toUpperCase()', desc: 'Convert to uppercase', snippet: 'toUpperCase()' },
            { name: 'toLowerCase()', desc: 'Convert to lowercase', snippet: 'toLowerCase()' },
            { name: 'trim()', desc: 'Trim whitespace', snippet: 'trim()' },
            { name: 'toString()', desc: 'Convert to string', snippet: 'toString()' },
        ];

        for (const helper of helpers) {
            const item = new vscode.CompletionItem(helper.name, vscode.CompletionItemKind.Method);
            item.detail = helper.desc;
            item.insertText = helper.snippet;
            item.sortText = `z_${helper.name}`; // Sort helpers last
            items.push(item);
        }

        return items;
    }

    /**
     * Create a completion item for an attribute value
     */
    private createValueItem(value: string, detail: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(value, vscode.CompletionItemKind.EnumMember);
        item.detail = detail;
        return item;
    }

    /**
     * Format attribute documentation
     */
    private formatAttributeDoc(attr: AttributeSchema): string {
        let doc = attr.description;

        if (attr.type) {
            doc += `\n\n**Type:** \`${attr.type}\``;
        }

        if (attr.values) {
            doc += `\n\n**Values:** ${attr.values.map(v => `\`${v}\``).join(', ')}`;
        }

        if (attr.default) {
            doc += `\n\n**Default:** \`${attr.default}\``;
        }

        return doc;
    }
}

/**
 * Register the completion provider
 */
export function registerCompletionProvider(context: vscode.ExtensionContext): void {
    const provider = new QuantumCompletionProvider();

    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            { language: 'quantum', scheme: 'file' },
            provider,
            '<', // Trigger on <
            ' ', // Trigger on space (for attributes)
            '"', // Trigger on " (for attribute values)
            "'", // Trigger on '
            '{', // Trigger on { (for databinding)
            '/'  // Trigger on / (for closing tags)
        )
    );
}
