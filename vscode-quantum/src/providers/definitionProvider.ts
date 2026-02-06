/**
 * Definition Provider for Quantum Language
 *
 * Provides Go to Definition for:
 * - Function references (jump to q:function)
 * - Component references (jump to q:component)
 * - Variable references (jump to q:set)
 * - Imported components (jump to import statement or file)
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { createParser } from '../language/quantumParser';
import { findDefinition, extractImportedComponents } from '../utils/documentUtils';

export class QuantumDefinitionProvider implements vscode.DefinitionProvider {

    async provideDefinition(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): Promise<vscode.Definition | vscode.LocationLink[] | undefined> {

        // Get the word at cursor position
        const wordRange = document.getWordRangeAtPosition(position, /[a-zA-Z_][\w]*/);
        if (!wordRange) return undefined;

        const word = document.getText(wordRange);

        // Try to find definition in current document
        const localDef = findDefinition(document, word);
        if (localDef) {
            return localDef;
        }

        // Check if it's a component call (PascalCase tag)
        const line = document.lineAt(position.line).text;
        const tagMatch = line.match(new RegExp(`<(${word})(?:\\s|/|>)`));

        if (tagMatch) {
            // Check if it's an imported component
            const imports = extractImportedComponents(document);
            const importInfo = imports.get(word);

            if (importInfo && importInfo.from) {
                // Try to resolve the import path
                const importPath = await this.resolveImportPath(document, importInfo.from);
                if (importPath) {
                    // Open the file and find the component definition
                    try {
                        const importedDoc = await vscode.workspace.openTextDocument(importPath);
                        const componentDef = findDefinition(importedDoc, importInfo.component);
                        if (componentDef) {
                            return componentDef;
                        }
                        // Return start of file if component not found
                        return new vscode.Location(vscode.Uri.file(importPath), new vscode.Position(0, 0));
                    } catch (e) {
                        // File not found
                    }
                }
            }

            // Check if it's defined in the same file
            const samFileComponent = findDefinition(document, word);
            if (samFileComponent) {
                return samFileComponent;
            }
        }

        // Check if it's a reference in a databinding expression or attribute value
        const parser = createParser(document);
        const cursorContext = parser.getCursorContext(position);

        if (cursorContext.inDataBinding || cursorContext.inAttributeValue) {
            // Try to find variable/function definition
            const parseResult = parser.parse();

            // Check variables
            const varDef = parseResult.variables.get(word);
            if (varDef) {
                return new vscode.Location(document.uri, varDef.range.start);
            }

            // Check functions
            const funcDef = parseResult.functions.get(word);
            if (funcDef) {
                return new vscode.Location(document.uri, funcDef.range.start);
            }

            // Check if it's a query reference
            const text = document.getText();
            const queryMatch = text.match(new RegExp(`<q:query[^>]*name="${word}"`));
            if (queryMatch) {
                const offset = queryMatch.index || 0;
                return new vscode.Location(document.uri, document.positionAt(offset));
            }
        }

        // Check handler attributes (on-click, on-submit, etc.)
        if (cursorContext.inAttributeValue && cursorContext.attributeName?.startsWith('on-')) {
            const funcDef = findDefinition(document, word);
            if (funcDef) {
                return funcDef;
            }
        }

        return undefined;
    }

    /**
     * Resolve an import path relative to the document
     */
    private async resolveImportPath(document: vscode.TextDocument, importPath: string): Promise<string | undefined> {
        const documentDir = path.dirname(document.uri.fsPath);

        // Try different extensions
        const extensions = ['.q', '/index.q', ''];

        for (const ext of extensions) {
            const fullPath = path.resolve(documentDir, importPath + ext);
            try {
                await vscode.workspace.fs.stat(vscode.Uri.file(fullPath));
                return fullPath;
            } catch (e) {
                // File doesn't exist, try next extension
            }
        }

        // Try components directory
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
        if (workspaceFolder) {
            const componentsPath = path.join(workspaceFolder.uri.fsPath, 'components', importPath);
            for (const ext of extensions) {
                const fullPath = componentsPath + ext;
                try {
                    await vscode.workspace.fs.stat(vscode.Uri.file(fullPath));
                    return fullPath;
                } catch (e) {
                    // File doesn't exist, try next extension
                }
            }
        }

        return undefined;
    }
}

/**
 * Register the definition provider
 */
export function registerDefinitionProvider(context: vscode.ExtensionContext): void {
    const provider = new QuantumDefinitionProvider();

    context.subscriptions.push(
        vscode.languages.registerDefinitionProvider(
            { language: 'quantum', scheme: 'file' },
            provider
        )
    );
}

/**
 * Reference Provider - Find all references to a symbol
 */
export class QuantumReferenceProvider implements vscode.ReferenceProvider {

    provideReferences(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.ReferenceContext,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Location[]> {

        const wordRange = document.getWordRangeAtPosition(position, /[a-zA-Z_][\w]*/);
        if (!wordRange) return [];

        const word = document.getText(wordRange);
        const locations: vscode.Location[] = [];
        const text = document.getText();

        // Find all occurrences of the word
        // In attribute values
        const attrPattern = new RegExp(`["']([^"']*\\b${word}\\b[^"']*)["']`, 'g');
        let match: RegExpExecArray | null;

        while ((match = attrPattern.exec(text)) !== null) {
            // Find the exact position of the word within the match
            const matchStart = match.index + 1; // +1 for opening quote
            const content = match[1];
            let wordIndex = 0;
            let searchStart = 0;

            while ((wordIndex = content.indexOf(word, searchStart)) !== -1) {
                // Check if it's a whole word
                const before = wordIndex > 0 ? content[wordIndex - 1] : ' ';
                const after = wordIndex + word.length < content.length ? content[wordIndex + word.length] : ' ';

                if (!/\w/.test(before) && !/\w/.test(after)) {
                    const start = document.positionAt(matchStart + wordIndex);
                    const end = document.positionAt(matchStart + wordIndex + word.length);
                    locations.push(new vscode.Location(document.uri, new vscode.Range(start, end)));
                }

                searchStart = wordIndex + 1;
            }
        }

        // In databinding expressions
        const bindPattern = new RegExp(`\\{[^}]*\\b${word}\\b[^}]*\\}`, 'g');
        while ((match = bindPattern.exec(text)) !== null) {
            const exprStart = match.index;
            const expr = match[0];
            const wordIndex = expr.indexOf(word);

            if (wordIndex !== -1) {
                const start = document.positionAt(exprStart + wordIndex);
                const end = document.positionAt(exprStart + wordIndex + word.length);
                locations.push(new vscode.Location(document.uri, new vscode.Range(start, end)));
            }
        }

        // Include definition if requested
        if (context.includeDeclaration) {
            const def = findDefinition(document, word);
            if (def) {
                locations.unshift(def);
            }
        }

        return locations;
    }
}

/**
 * Register the reference provider
 */
export function registerReferenceProvider(context: vscode.ExtensionContext): void {
    const provider = new QuantumReferenceProvider();

    context.subscriptions.push(
        vscode.languages.registerReferenceProvider(
            { language: 'quantum', scheme: 'file' },
            provider
        )
    );
}
