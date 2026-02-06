/**
 * Simple Quantum Document Parser
 *
 * Provides parsing utilities for Quantum files to support
 * IntelliSense, diagnostics, and go-to-definition features.
 */

import * as vscode from 'vscode';

/**
 * Represents a parsed tag in the document
 */
export interface ParsedTag {
    name: string;           // Full tag name (e.g., "q:component", "ui:button")
    namespace: string;      // Namespace prefix (e.g., "q", "ui")
    localName: string;      // Local name without prefix (e.g., "component", "button")
    attributes: Map<string, ParsedAttribute>;
    startPosition: vscode.Position;
    endPosition: vscode.Position;
    isSelfClosing: boolean;
    isClosingTag: boolean;
    range: vscode.Range;
}

/**
 * Represents a parsed attribute
 */
export interface ParsedAttribute {
    name: string;
    value: string;
    hasValue: boolean;
    valueRange?: vscode.Range;
    nameRange: vscode.Range;
    hasDataBinding: boolean;
}

/**
 * Represents a defined function in the document
 */
export interface FunctionDefinition {
    name: string;
    range: vscode.Range;
    params: string[];
    returnType?: string;
}

/**
 * Represents a defined component in the document
 */
export interface ComponentDefinition {
    name: string;
    range: vscode.Range;
    params: string[];
    type?: string;
}

/**
 * Represents a variable definition
 */
export interface VariableDefinition {
    name: string;
    range: vscode.Range;
    type?: string;
    scope?: string;
}

/**
 * Parse result for a document
 */
export interface DocumentParseResult {
    tags: ParsedTag[];
    functions: Map<string, FunctionDefinition>;
    components: Map<string, ComponentDefinition>;
    variables: Map<string, VariableDefinition>;
    imports: Map<string, { from?: string; range: vscode.Range }>;
    errors: ParseError[];
}

/**
 * Parse error
 */
export interface ParseError {
    message: string;
    range: vscode.Range;
    severity: 'error' | 'warning';
}

/**
 * Context at cursor position
 */
export interface CursorContext {
    inTag: boolean;
    tagName?: string;
    inAttribute: boolean;
    attributeName?: string;
    inAttributeValue: boolean;
    attributeValue?: string;
    inDataBinding: boolean;
    expressionPrefix?: string;
    position: vscode.Position;
}

/**
 * Parser for Quantum documents
 */
export class QuantumParser {
    private document: vscode.TextDocument;

    constructor(document: vscode.TextDocument) {
        this.document = document;
    }

    /**
     * Parse the entire document
     */
    public parse(): DocumentParseResult {
        const text = this.document.getText();
        const result: DocumentParseResult = {
            tags: [],
            functions: new Map(),
            components: new Map(),
            variables: new Map(),
            imports: new Map(),
            errors: []
        };

        // Parse all tags
        const tagPattern = /<(\/?)([a-zA-Z_:][\w:\-]*)([^>]*?)(\/?)>/g;
        let match: RegExpExecArray | null;

        while ((match = tagPattern.exec(text)) !== null) {
            const isClosing = match[1] === '/';
            const fullName = match[2];
            const attrsString = match[3];
            const isSelfClosing = match[4] === '/';

            const startOffset = match.index;
            const endOffset = startOffset + match[0].length;
            const startPos = this.document.positionAt(startOffset);
            const endPos = this.document.positionAt(endOffset);

            // Parse namespace and local name
            const [namespace, localName] = this.parseTagName(fullName);

            // Parse attributes
            const attributes = this.parseAttributes(attrsString, startOffset + match[0].indexOf(attrsString));

            const tag: ParsedTag = {
                name: fullName,
                namespace,
                localName,
                attributes,
                startPosition: startPos,
                endPosition: endPos,
                isSelfClosing,
                isClosingTag: isClosing,
                range: new vscode.Range(startPos, endPos)
            };

            result.tags.push(tag);

            // Extract definitions
            if (!isClosing) {
                this.extractDefinitions(tag, result);
            }
        }

        // Validate document
        this.validateDocument(result);

        return result;
    }

    /**
     * Parse tag name into namespace and local name
     */
    private parseTagName(fullName: string): [string, string] {
        const colonIndex = fullName.indexOf(':');
        if (colonIndex > 0) {
            return [fullName.substring(0, colonIndex), fullName.substring(colonIndex + 1)];
        }
        // No namespace - could be HTML or component call
        if (fullName[0] === fullName[0].toUpperCase()) {
            return ['component', fullName];
        }
        return ['html', fullName];
    }

    /**
     * Parse attributes from attribute string
     */
    private parseAttributes(attrsString: string, baseOffset: number): Map<string, ParsedAttribute> {
        const attributes = new Map<string, ParsedAttribute>();

        // Pattern for attributes: name="value" or name='value' or just name
        const attrPattern = /([a-zA-Z_:][a-zA-Z0-9_:\-]*)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'))?/g;
        let match: RegExpExecArray | null;

        while ((match = attrPattern.exec(attrsString)) !== null) {
            const name = match[1];
            const value = match[2] ?? match[3] ?? '';
            const hasValue = match[2] !== undefined || match[3] !== undefined;

            const nameStart = baseOffset + match.index;
            const nameEnd = nameStart + name.length;
            const nameRange = new vscode.Range(
                this.document.positionAt(nameStart),
                this.document.positionAt(nameEnd)
            );

            let valueRange: vscode.Range | undefined;
            if (hasValue) {
                const valueStart = nameStart + match[0].indexOf(value);
                const valueEnd = valueStart + value.length;
                valueRange = new vscode.Range(
                    this.document.positionAt(valueStart),
                    this.document.positionAt(valueEnd)
                );
            }

            attributes.set(name, {
                name,
                value,
                hasValue,
                nameRange,
                valueRange,
                hasDataBinding: value.includes('{') && value.includes('}')
            });
        }

        return attributes;
    }

    /**
     * Extract definitions (functions, components, variables) from a tag
     */
    private extractDefinitions(tag: ParsedTag, result: DocumentParseResult): void {
        // Extract function definitions
        if (tag.name === 'q:function') {
            const nameAttr = tag.attributes.get('name');
            if (nameAttr) {
                const params: string[] = [];
                // Would need to parse child q:param elements for full accuracy
                result.functions.set(nameAttr.value, {
                    name: nameAttr.value,
                    range: tag.range,
                    params,
                    returnType: tag.attributes.get('returnType')?.value
                });
            }
        }

        // Extract component definitions
        if (tag.name === 'q:component') {
            const nameAttr = tag.attributes.get('name');
            if (nameAttr) {
                result.components.set(nameAttr.value, {
                    name: nameAttr.value,
                    range: tag.range,
                    params: [],
                    type: tag.attributes.get('type')?.value
                });
            }
        }

        // Extract variable definitions
        if (tag.name === 'q:set') {
            const nameAttr = tag.attributes.get('name');
            if (nameAttr) {
                result.variables.set(nameAttr.value, {
                    name: nameAttr.value,
                    range: tag.range,
                    type: tag.attributes.get('type')?.value,
                    scope: tag.attributes.get('scope')?.value
                });
            }
        }

        // Extract imports
        if (tag.name === 'q:import') {
            const componentAttr = tag.attributes.get('component');
            const fromAttr = tag.attributes.get('from');
            const asAttr = tag.attributes.get('as');
            if (componentAttr) {
                const alias = asAttr?.value || componentAttr.value;
                result.imports.set(alias, {
                    from: fromAttr?.value,
                    range: tag.range
                });
            }
        }
    }

    /**
     * Validate document and collect errors
     */
    private validateDocument(result: DocumentParseResult): void {
        const tagStack: ParsedTag[] = [];

        for (const tag of result.tags) {
            if (tag.isClosingTag) {
                // Check for matching opening tag
                const lastOpen = tagStack.pop();
                if (!lastOpen || lastOpen.name !== tag.name) {
                    result.errors.push({
                        message: lastOpen
                            ? `Unexpected closing tag </${tag.name}>. Expected </${lastOpen.name}>`
                            : `Unexpected closing tag </${tag.name}> with no matching opening tag`,
                        range: tag.range,
                        severity: 'error'
                    });
                }
            } else if (!tag.isSelfClosing) {
                tagStack.push(tag);
            }

            // Check required attributes
            this.validateRequiredAttributes(tag, result);
        }

        // Check for unclosed tags
        for (const unclosed of tagStack) {
            result.errors.push({
                message: `Unclosed tag <${unclosed.name}>`,
                range: unclosed.range,
                severity: 'error'
            });
        }
    }

    /**
     * Validate required attributes for a tag
     */
    private validateRequiredAttributes(tag: ParsedTag, result: DocumentParseResult): void {
        // Skip closing tags
        if (tag.isClosingTag) return;

        // Import the schema (would need dynamic import in real implementation)
        const requiredAttrs: { [key: string]: string[] } = {
            'q:component': ['name'],
            'q:application': ['id'],
            'q:function': ['name'],
            'q:query': ['name'],
            'q:set': ['name'],
            'q:import': ['component'],
            'q:param': ['name'],
            'q:redirect': ['url'],
            'q:invoke': ['name'],
            'ui:input': ['bind'],
            'ui:image': ['src'],
            'ui:link': ['to'],
            'ui:column': ['key'],
            'ui:validator': ['name', 'message'],
        };

        const required = requiredAttrs[tag.name];
        if (required) {
            for (const attr of required) {
                if (!tag.attributes.has(attr)) {
                    result.errors.push({
                        message: `Missing required attribute "${attr}" on <${tag.name}>`,
                        range: tag.range,
                        severity: 'error'
                    });
                }
            }
        }
    }

    /**
     * Get cursor context for IntelliSense
     */
    public getCursorContext(position: vscode.Position): CursorContext {
        const text = this.document.getText();
        const offset = this.document.offsetAt(position);

        // Find the start of the current tag (if any)
        let tagStart = -1;
        let depth = 0;
        for (let i = offset - 1; i >= 0; i--) {
            if (text[i] === '>') {
                if (depth === 0) break;
                depth--;
            } else if (text[i] === '<') {
                if (depth === 0) {
                    tagStart = i;
                    break;
                }
                depth++;
            }
        }

        // Not inside a tag
        if (tagStart === -1) {
            return {
                inTag: false,
                inAttribute: false,
                inAttributeValue: false,
                inDataBinding: false,
                position
            };
        }

        // Check if we're past the tag end
        const textFromTag = text.substring(tagStart, offset);
        if (textFromTag.includes('>')) {
            return {
                inTag: false,
                inAttribute: false,
                inAttributeValue: false,
                inDataBinding: false,
                position
            };
        }

        // Extract tag name
        const tagNameMatch = textFromTag.match(/^<\/?([a-zA-Z_:][\w:\-]*)/);
        const tagName = tagNameMatch ? tagNameMatch[1] : undefined;

        // Check if we're in an attribute value
        const beforeCursor = textFromTag;

        // Check for unclosed attribute value
        const lastQuote = Math.max(
            beforeCursor.lastIndexOf('"'),
            beforeCursor.lastIndexOf("'")
        );
        const lastEquals = beforeCursor.lastIndexOf('=');

        if (lastQuote > lastEquals) {
            // We might be inside a quoted value - check if it's closed
            const quoteChar = beforeCursor[lastQuote];
            const afterQuote = beforeCursor.substring(lastQuote + 1);
            if (!afterQuote.includes(quoteChar)) {
                // Inside attribute value
                const attrMatch = beforeCursor.substring(0, lastEquals).match(/([a-zA-Z_:][a-zA-Z0-9_:\-]*)\s*$/);
                const attributeName = attrMatch ? attrMatch[1] : undefined;
                const valueContent = afterQuote;

                // Check for databinding
                const lastOpenBrace = valueContent.lastIndexOf('{');
                const lastCloseBrace = valueContent.lastIndexOf('}');
                const inDataBinding = lastOpenBrace > lastCloseBrace;

                return {
                    inTag: true,
                    tagName,
                    inAttribute: true,
                    attributeName,
                    inAttributeValue: true,
                    attributeValue: valueContent,
                    inDataBinding,
                    expressionPrefix: inDataBinding ? valueContent.substring(lastOpenBrace + 1) : undefined,
                    position
                };
            }
        }

        // In tag but not in attribute value - might be typing attribute name
        const lastSpace = beforeCursor.lastIndexOf(' ');
        const partialAttr = beforeCursor.substring(lastSpace + 1);

        return {
            inTag: true,
            tagName,
            inAttribute: !partialAttr.includes('='),
            attributeName: partialAttr.includes('=') ? undefined : partialAttr.replace(/[<\/>]/g, ''),
            inAttributeValue: false,
            inDataBinding: false,
            position
        };
    }

    /**
     * Find tag at a specific position
     */
    public getTagAtPosition(position: vscode.Position): ParsedTag | undefined {
        const result = this.parse();
        for (const tag of result.tags) {
            if (tag.range.contains(position)) {
                return tag;
            }
        }
        return undefined;
    }

    /**
     * Find all references to a symbol (function, component, variable)
     */
    public findReferences(symbolName: string): vscode.Range[] {
        const ranges: vscode.Range[] = [];
        const text = this.document.getText();

        // Search for references in attribute values
        const pattern = new RegExp(`["']([^"']*\\{[^}]*\\b${symbolName}\\b[^}]*\\}[^"']*|${symbolName})["']`, 'g');
        let match: RegExpExecArray | null;

        while ((match = pattern.exec(text)) !== null) {
            const start = this.document.positionAt(match.index);
            const end = this.document.positionAt(match.index + match[0].length);
            ranges.push(new vscode.Range(start, end));
        }

        return ranges;
    }

    /**
     * Get all databinding expressions in the document
     */
    public getDataBindingExpressions(): Array<{ expression: string; range: vscode.Range }> {
        const expressions: Array<{ expression: string; range: vscode.Range }> = [];
        const text = this.document.getText();

        const pattern = /\{([^}]+)\}/g;
        let match: RegExpExecArray | null;

        while ((match = pattern.exec(text)) !== null) {
            const start = this.document.positionAt(match.index);
            const end = this.document.positionAt(match.index + match[0].length);
            expressions.push({
                expression: match[1],
                range: new vscode.Range(start, end)
            });
        }

        return expressions;
    }
}

/**
 * Create a parser for a document
 */
export function createParser(document: vscode.TextDocument): QuantumParser {
    return new QuantumParser(document);
}
