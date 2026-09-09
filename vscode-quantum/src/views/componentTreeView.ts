/**
 * Quantum Component Tree View
 *
 * TreeView in sidebar showing component structure.
 * Shows: components, functions, variables, UI elements.
 * Click to navigate to definition.
 */

import * as vscode from 'vscode';
import * as path from 'path';

/**
 * Tree item types for Quantum elements
 */
export enum QuantumNodeType {
    Component = 'component',
    Function = 'function',
    Variable = 'variable',
    Query = 'query',
    Loop = 'loop',
    Conditional = 'conditional',
    UIElement = 'ui-element',
    Action = 'action',
    Include = 'include',
    Slot = 'slot',
    Template = 'template'
}

/**
 * Represents a node in the Quantum component tree
 */
export class QuantumTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly nodeType: QuantumNodeType,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly range: vscode.Range,
        public readonly children: QuantumTreeItem[] = [],
        public readonly attributes: Map<string, string> = new Map()
    ) {
        super(label, collapsibleState);

        this.tooltip = this._getTooltip();
        this.iconPath = this._getIcon();
        this.contextValue = nodeType;

        // Make item clickable to navigate
        this.command = {
            command: 'quantum.goToDefinition',
            title: 'Go to Definition',
            arguments: [range]
        };
    }

    private _getTooltip(): string {
        const attrs = Array.from(this.attributes.entries())
            .map(([k, v]) => `${k}="${v}"`)
            .join(' ');

        if (attrs) {
            return `<q:${this.nodeType} ${attrs}>`;
        }
        return `<q:${this.nodeType}>`;
    }

    private _getIcon(): vscode.ThemeIcon {
        switch (this.nodeType) {
            case QuantumNodeType.Component:
                return new vscode.ThemeIcon('symbol-class', new vscode.ThemeColor('symbolIcon.classForeground'));
            case QuantumNodeType.Function:
                return new vscode.ThemeIcon('symbol-method', new vscode.ThemeColor('symbolIcon.methodForeground'));
            case QuantumNodeType.Variable:
                return new vscode.ThemeIcon('symbol-variable', new vscode.ThemeColor('symbolIcon.variableForeground'));
            case QuantumNodeType.Query:
                return new vscode.ThemeIcon('database', new vscode.ThemeColor('symbolIcon.fieldForeground'));
            case QuantumNodeType.Loop:
                return new vscode.ThemeIcon('sync', new vscode.ThemeColor('symbolIcon.enumeratorForeground'));
            case QuantumNodeType.Conditional:
                return new vscode.ThemeIcon('git-compare', new vscode.ThemeColor('symbolIcon.operatorForeground'));
            case QuantumNodeType.UIElement:
                return new vscode.ThemeIcon('symbol-interface', new vscode.ThemeColor('symbolIcon.interfaceForeground'));
            case QuantumNodeType.Action:
                return new vscode.ThemeIcon('zap', new vscode.ThemeColor('symbolIcon.eventForeground'));
            case QuantumNodeType.Include:
                return new vscode.ThemeIcon('file-symlink-file', new vscode.ThemeColor('symbolIcon.fileForeground'));
            case QuantumNodeType.Slot:
                return new vscode.ThemeIcon('symbol-property', new vscode.ThemeColor('symbolIcon.propertyForeground'));
            case QuantumNodeType.Template:
                return new vscode.ThemeIcon('code', new vscode.ThemeColor('symbolIcon.snippetForeground'));
            default:
                return new vscode.ThemeIcon('symbol-misc');
        }
    }
}

/**
 * Data provider for the Quantum component tree
 */
export class QuantumTreeDataProvider implements vscode.TreeDataProvider<QuantumTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<QuantumTreeItem | undefined | null | void> =
        new vscode.EventEmitter<QuantumTreeItem | undefined | null | void>();

    readonly onDidChangeTreeData: vscode.Event<QuantumTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    private _rootItems: QuantumTreeItem[] = [];
    private _currentDocument: vscode.TextDocument | undefined;

    constructor() {
        // Listen for document changes
        vscode.workspace.onDidChangeTextDocument(e => {
            if (e.document === this._currentDocument) {
                this._parseDocument(e.document);
            }
        });

        // Listen for active editor changes
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor && editor.document.languageId === 'quantum') {
                this._parseDocument(editor.document);
            }
        });

        // Parse initial document
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'quantum') {
            this._parseDocument(editor.document);
        }
    }

    refresh(): void {
        if (this._currentDocument) {
            this._parseDocument(this._currentDocument);
        }
    }

    getTreeItem(element: QuantumTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: QuantumTreeItem): Thenable<QuantumTreeItem[]> {
        if (element) {
            return Promise.resolve(element.children);
        }
        return Promise.resolve(this._rootItems);
    }

    getParent(element: QuantumTreeItem): vscode.ProviderResult<QuantumTreeItem> {
        // Search for parent in tree
        const findParent = (items: QuantumTreeItem[], target: QuantumTreeItem): QuantumTreeItem | undefined => {
            for (const item of items) {
                if (item.children.includes(target)) {
                    return item;
                }
                const found = findParent(item.children, target);
                if (found) {
                    return found;
                }
            }
            return undefined;
        };

        return findParent(this._rootItems, element);
    }

    private _parseDocument(document: vscode.TextDocument): void {
        this._currentDocument = document;
        this._rootItems = [];

        const text = document.getText();
        const lines = text.split('\n');

        // Track nesting
        const stack: QuantumTreeItem[] = [];

        for (let lineNum = 0; lineNum < lines.length; lineNum++) {
            const line = lines[lineNum];
            const trimmed = line.trim();

            // Skip empty lines and comments
            if (!trimmed || trimmed.startsWith('<!--')) {
                continue;
            }

            // Parse Quantum tags
            const tagInfo = this._parseTag(trimmed, lineNum, line);
            if (tagInfo) {
                const { item, isClosing, isSelfClosing } = tagInfo;

                if (isClosing) {
                    // Pop from stack
                    stack.pop();
                } else if (item) {
                    // Add to parent or root
                    if (stack.length > 0) {
                        stack[stack.length - 1].children.push(item);
                    } else {
                        this._rootItems.push(item);
                    }

                    // Push to stack if not self-closing
                    if (!isSelfClosing) {
                        stack.push(item);
                    }
                }
            }
        }

        this._onDidChangeTreeData.fire();
    }

    private _parseTag(line: string, lineNum: number, fullLine: string): {
        item: QuantumTreeItem | null;
        isClosing: boolean;
        isSelfClosing: boolean;
    } | null {
        // Check for closing tag
        const closingMatch = line.match(/^<\/q:(\w+)>/);
        if (closingMatch) {
            return { item: null, isClosing: true, isSelfClosing: false };
        }

        // Parse opening tag
        const tagMatch = line.match(/^<q:(\w+)([^>]*?)(\/?)>/);
        if (!tagMatch) {
            // Check for HTML elements
            const htmlMatch = line.match(/^<(\w+)([^>]*?)(\/?)>/);
            if (htmlMatch && !htmlMatch[1].startsWith('q:')) {
                const [, tagName, attrsStr, selfClose] = htmlMatch;
                const attrs = this._parseAttributes(attrsStr);
                const startCol = fullLine.indexOf('<');
                const range = new vscode.Range(lineNum, startCol, lineNum, fullLine.length);

                const label = attrs.get('id') || attrs.get('class') || tagName;

                return {
                    item: new QuantumTreeItem(
                        label,
                        QuantumNodeType.UIElement,
                        vscode.TreeItemCollapsibleState.Collapsed,
                        range,
                        [],
                        attrs
                    ),
                    isClosing: false,
                    isSelfClosing: selfClose === '/'
                };
            }
            return null;
        }

        const [, tagName, attrsStr, selfClose] = tagMatch;
        const attrs = this._parseAttributes(attrsStr);
        const startCol = fullLine.indexOf('<');
        const range = new vscode.Range(lineNum, startCol, lineNum, fullLine.length);

        const nodeType = this._getNodeType(tagName);
        const label = this._getLabel(tagName, attrs);
        const collapsible = selfClose === '/'
            ? vscode.TreeItemCollapsibleState.None
            : vscode.TreeItemCollapsibleState.Collapsed;

        const item = new QuantumTreeItem(
            label,
            nodeType,
            collapsible,
            range,
            [],
            attrs
        );

        return {
            item,
            isClosing: false,
            isSelfClosing: selfClose === '/'
        };
    }

    private _parseAttributes(attrsStr: string): Map<string, string> {
        const attrs = new Map<string, string>();
        const regex = /(\w+)="([^"]*)"/g;
        let match;

        while ((match = regex.exec(attrsStr)) !== null) {
            attrs.set(match[1], match[2]);
        }

        return attrs;
    }

    private _getNodeType(tagName: string): QuantumNodeType {
        const typeMap: { [key: string]: QuantumNodeType } = {
            'component': QuantumNodeType.Component,
            'function': QuantumNodeType.Function,
            'set': QuantumNodeType.Variable,
            'query': QuantumNodeType.Query,
            'loop': QuantumNodeType.Loop,
            'if': QuantumNodeType.Conditional,
            'else': QuantumNodeType.Conditional,
            'elseif': QuantumNodeType.Conditional,
            'action': QuantumNodeType.Action,
            'include': QuantumNodeType.Include,
            'slot': QuantumNodeType.Slot,
            'template': QuantumNodeType.Template,
            'output': QuantumNodeType.UIElement,
            'form': QuantumNodeType.UIElement,
            'input': QuantumNodeType.UIElement,
            'button': QuantumNodeType.UIElement
        };

        return typeMap[tagName] || QuantumNodeType.UIElement;
    }

    private _getLabel(tagName: string, attrs: Map<string, string>): string {
        // Use name attribute if available
        if (attrs.has('name')) {
            return `${tagName}: ${attrs.get('name')}`;
        }

        // Use var attribute for set
        if (tagName === 'set' && attrs.has('var')) {
            return `${attrs.get('var')} = ${attrs.get('value') || '...'}`;
        }

        // Use test for conditionals
        if ((tagName === 'if' || tagName === 'elseif') && attrs.has('test')) {
            return `if: ${attrs.get('test')}`;
        }

        // Use from/to for loops
        if (tagName === 'loop') {
            const from = attrs.get('from') || attrs.get('array');
            const to = attrs.get('to') || attrs.get('item');
            if (from && to) {
                return `loop: ${from} to ${to}`;
            }
        }

        // Use value for output
        if (tagName === 'output' && attrs.has('value')) {
            const value = attrs.get('value')!;
            return `output: ${value.length > 20 ? value.substring(0, 20) + '...' : value}`;
        }

        return tagName;
    }
}

/**
 * Register the component tree view
 */
export function registerComponentTreeView(context: vscode.ExtensionContext): QuantumTreeDataProvider {
    const treeDataProvider = new QuantumTreeDataProvider();

    const treeView = vscode.window.createTreeView('quantumComponentTree', {
        treeDataProvider,
        showCollapseAll: true
    });

    // Register refresh command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.refreshComponentTree', () => {
            treeDataProvider.refresh();
        })
    );

    // Register go to definition command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.goToDefinition', (range: vscode.Range) => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                editor.selection = new vscode.Selection(range.start, range.end);
                editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
            }
        })
    );

    context.subscriptions.push(treeView);

    return treeDataProvider;
}
