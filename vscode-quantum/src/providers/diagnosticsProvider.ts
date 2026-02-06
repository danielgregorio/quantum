/**
 * Diagnostics Provider for Quantum Language
 *
 * Provides linting/diagnostics for:
 * - Missing required attributes
 * - Invalid attribute values
 * - Unclosed tags
 * - Undefined variable references
 * - Unknown tags
 */

import * as vscode from 'vscode';
import {
    getTagSchema,
    getAttributeSchema,
    getRequiredAttributes,
    tagsByName
} from '../language/quantumSchema';
import { createParser, ParseError } from '../language/quantumParser';
import { extractVariableNames, extractFunctionNames } from '../utils/documentUtils';

let diagnosticCollection: vscode.DiagnosticCollection;

/**
 * Run diagnostics on a document
 */
export function diagnoseDocument(document: vscode.TextDocument): void {
    if (document.languageId !== 'quantum') return;

    const diagnostics: vscode.Diagnostic[] = [];
    const parser = createParser(document);
    const parseResult = parser.parse();

    // Add parse errors
    for (const error of parseResult.errors) {
        const severity = error.severity === 'error'
            ? vscode.DiagnosticSeverity.Error
            : vscode.DiagnosticSeverity.Warning;

        diagnostics.push(new vscode.Diagnostic(error.range, error.message, severity));
    }

    // Validate tags
    for (const tag of parseResult.tags) {
        if (tag.isClosingTag) continue;

        const tagDiagnostics = validateTag(document, tag, parseResult);
        diagnostics.push(...tagDiagnostics);
    }

    // Validate databinding expressions
    const expressions = parser.getDataBindingExpressions();
    const definedVars = extractVariableNames(document);
    const definedFuncs = extractFunctionNames(document);

    for (const expr of expressions) {
        const exprDiagnostics = validateExpression(expr, definedVars, definedFuncs);
        diagnostics.push(...exprDiagnostics);
    }

    diagnosticCollection.set(document.uri, diagnostics);
}

/**
 * Validate a single tag
 */
function validateTag(
    document: vscode.TextDocument,
    tag: { name: string; attributes: Map<string, { name: string; value: string; hasValue: boolean; nameRange: vscode.Range; valueRange?: vscode.Range }>; range: vscode.Range },
    parseResult: ReturnType<ReturnType<typeof createParser>['parse']>
): vscode.Diagnostic[] {
    const diagnostics: vscode.Diagnostic[] = [];
    const schema = getTagSchema(tag.name);

    // Check if tag is known
    if (!schema && tag.name.includes(':')) {
        const [namespace] = tag.name.split(':');
        if (['q', 'ui', 'qg', 'qt', 'qtest'].includes(namespace)) {
            diagnostics.push(new vscode.Diagnostic(
                tag.range,
                `Unknown tag: <${tag.name}>`,
                vscode.DiagnosticSeverity.Warning
            ));
        }
    }

    if (!schema) return diagnostics;

    // Check required attributes
    const requiredAttrs = getRequiredAttributes(tag.name);
    for (const attrName of requiredAttrs) {
        if (!tag.attributes.has(attrName)) {
            diagnostics.push(new vscode.Diagnostic(
                tag.range,
                `Missing required attribute "${attrName}" on <${tag.name}>`,
                vscode.DiagnosticSeverity.Error
            ));
        }
    }

    // Validate attribute values
    for (const [attrName, attr] of tag.attributes) {
        const attrSchema = getAttributeSchema(tag.name, attrName);

        // Unknown attribute warning (only for Quantum tags)
        if (!attrSchema && tag.name.includes(':')) {
            // Some common attributes are always valid
            const commonAttrs = ['id', 'class', 'style', 'data-*'];
            if (!commonAttrs.some(c => c === attrName || (c.endsWith('*') && attrName.startsWith(c.slice(0, -1))))) {
                // Only warn if it's not a common HTML-like attribute
                if (!['title', 'name', 'value', 'href', 'src', 'alt', 'disabled', 'readonly'].includes(attrName)) {
                    diagnostics.push(new vscode.Diagnostic(
                        attr.nameRange,
                        `Unknown attribute "${attrName}" on <${tag.name}>`,
                        vscode.DiagnosticSeverity.Hint
                    ));
                }
            }
        }

        if (attrSchema && attr.hasValue && attr.valueRange) {
            // Validate enum values
            if (attrSchema.type === 'enum' && attrSchema.values) {
                const value = attr.value;
                // Skip databinding expressions
                if (!value.includes('{') && !attrSchema.values.includes(value)) {
                    diagnostics.push(new vscode.Diagnostic(
                        attr.valueRange,
                        `Invalid value "${value}" for "${attrName}". Expected: ${attrSchema.values.join(', ')}`,
                        vscode.DiagnosticSeverity.Error
                    ));
                }
            }

            // Validate boolean values
            if (attrSchema.type === 'boolean') {
                const value = attr.value.toLowerCase();
                if (!value.includes('{') && !['true', 'false', '1', '0', 'yes', 'no'].includes(value)) {
                    diagnostics.push(new vscode.Diagnostic(
                        attr.valueRange,
                        `Invalid boolean value "${attr.value}". Expected: true or false`,
                        vscode.DiagnosticSeverity.Error
                    ));
                }
            }

            // Validate number values
            if (attrSchema.type === 'number') {
                const value = attr.value;
                if (!value.includes('{') && isNaN(Number(value))) {
                    diagnostics.push(new vscode.Diagnostic(
                        attr.valueRange,
                        `Invalid number value "${value}"`,
                        vscode.DiagnosticSeverity.Error
                    ));
                }
            }
        }
    }

    // Tag-specific validation
    const tagSpecificDiagnostics = validateTagSpecific(tag, parseResult);
    diagnostics.push(...tagSpecificDiagnostics);

    return diagnostics;
}

/**
 * Tag-specific validation rules
 */
function validateTagSpecific(
    tag: { name: string; attributes: Map<string, { name: string; value: string; hasValue: boolean; nameRange: vscode.Range; valueRange?: vscode.Range }>; range: vscode.Range },
    parseResult: ReturnType<ReturnType<typeof createParser>['parse']>
): vscode.Diagnostic[] {
    const diagnostics: vscode.Diagnostic[] = [];

    switch (tag.name) {
        case 'q:function': {
            // Check for duplicate function names
            const name = tag.attributes.get('name')?.value;
            if (name) {
                let count = 0;
                for (const [funcName, func] of parseResult.functions) {
                    if (funcName === name) count++;
                }
                if (count > 1) {
                    diagnostics.push(new vscode.Diagnostic(
                        tag.range,
                        `Duplicate function name "${name}"`,
                        vscode.DiagnosticSeverity.Error
                    ));
                }
            }
            break;
        }

        case 'q:component': {
            // Check for valid component name (PascalCase)
            const name = tag.attributes.get('name')?.value;
            if (name && !/^[A-Z][a-zA-Z0-9]*$/.test(name)) {
                const nameAttr = tag.attributes.get('name');
                if (nameAttr?.valueRange) {
                    diagnostics.push(new vscode.Diagnostic(
                        nameAttr.valueRange,
                        `Component name "${name}" should be PascalCase`,
                        vscode.DiagnosticSeverity.Warning
                    ));
                }
            }
            break;
        }

        case 'q:loop': {
            // Check that range loops have from/to
            const type = tag.attributes.get('type')?.value || 'range';
            if (type === 'range') {
                if (!tag.attributes.has('from') || !tag.attributes.has('to')) {
                    diagnostics.push(new vscode.Diagnostic(
                        tag.range,
                        `Range loop requires both "from" and "to" attributes`,
                        vscode.DiagnosticSeverity.Error
                    ));
                }
            }
            // Check that array loops have items
            if (type === 'array' && !tag.attributes.has('items')) {
                diagnostics.push(new vscode.Diagnostic(
                    tag.range,
                    `Array loop requires "items" attribute`,
                    vscode.DiagnosticSeverity.Error
                ));
            }
            break;
        }

        case 'ui:input': {
            // Warn about missing validation for required inputs
            const required = tag.attributes.get('required')?.value;
            const errorMessage = tag.attributes.get('error-message')?.value;
            if (required === 'true' && !errorMessage) {
                diagnostics.push(new vscode.Diagnostic(
                    tag.range,
                    `Consider adding "error-message" for required input`,
                    vscode.DiagnosticSeverity.Hint
                ));
            }
            break;
        }

        case 'ui:tab': {
            // Tab should be inside tabpanel
            // This is a simplified check - would need parent tracking for accuracy
            break;
        }

        case 'q:else':
        case 'q:elseif': {
            // These should be inside q:if
            // This is a simplified check - would need parent tracking for accuracy
            break;
        }
    }

    return diagnostics;
}

/**
 * Validate a databinding expression
 */
function validateExpression(
    expr: { expression: string; range: vscode.Range },
    definedVars: Set<string>,
    definedFuncs: Set<string>
): vscode.Diagnostic[] {
    const diagnostics: vscode.Diagnostic[] = [];

    // Extract identifiers from the expression
    const identifiers = expr.expression.match(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g);
    if (!identifiers) return diagnostics;

    // Filter out keywords and built-ins
    const keywords = new Set([
        'true', 'false', 'null', 'undefined',
        'if', 'else', 'and', 'or', 'not',
        'length', 'toUpperCase', 'toLowerCase', 'trim', 'toString',
        'parseInt', 'parseFloat', 'Math', 'Date', 'JSON',
        'item', 'index', 'row', 'column', // Common loop variables
        'session', 'application', 'request', 'form' // Common scopes
    ]);

    for (const id of identifiers) {
        if (keywords.has(id)) continue;

        // Check if it's a known variable or function
        if (!definedVars.has(id) && !definedFuncs.has(id)) {
            // Don't warn for property access (e.g., user.name)
            const dotBefore = expr.expression.indexOf(`.${id}`) !== -1;
            const bracketBefore = expr.expression.indexOf(`[${id}]`) !== -1 || expr.expression.indexOf(`['${id}']`) !== -1;

            if (!dotBefore && !bracketBefore) {
                // Only warn, don't error - variable might be from parent scope
                diagnostics.push(new vscode.Diagnostic(
                    expr.range,
                    `Variable "${id}" may be undefined`,
                    vscode.DiagnosticSeverity.Warning
                ));
            }
        }
    }

    return diagnostics;
}

/**
 * Register diagnostics provider
 */
export function registerDiagnosticsProvider(context: vscode.ExtensionContext): void {
    diagnosticCollection = vscode.languages.createDiagnosticCollection('quantum');
    context.subscriptions.push(diagnosticCollection);

    // Diagnose on open
    if (vscode.window.activeTextEditor) {
        diagnoseDocument(vscode.window.activeTextEditor.document);
    }

    // Diagnose on change
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument(event => {
            diagnoseDocument(event.document);
        })
    );

    // Diagnose on open
    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument(document => {
            diagnoseDocument(document);
        })
    );

    // Clear on close
    context.subscriptions.push(
        vscode.workspace.onDidCloseTextDocument(document => {
            diagnosticCollection.delete(document.uri);
        })
    );

    // Diagnose all open documents
    vscode.workspace.textDocuments.forEach(diagnoseDocument);
}

/**
 * Clear all diagnostics
 */
export function clearDiagnostics(): void {
    diagnosticCollection.clear();
}
