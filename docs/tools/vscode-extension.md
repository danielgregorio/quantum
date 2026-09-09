# VS Code Extension

The Quantum VS Code extension provides syntax highlighting, IntelliSense, snippets, and live preview for Quantum development.

## Installation

### From Marketplace

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Quantum Framework"
4. Click Install

### From VSIX

```bash
# Install from local file
code --install-extension quantum-vscode-0.1.0.vsix
```

### Manual Setup

For development or custom installation:

1. Clone the extension repository
2. Run `npm install`
3. Run `npm run package`
4. Install the generated `.vsix` file

## Features

### Syntax Highlighting

Full syntax highlighting for `.q` files:

- XML tags and attributes
- Quantum-specific tags (`q:`, `ui:`)
- Data binding expressions (`{variable}`)
- SQL in `q:query` blocks
- Comments

**Screenshot description**: Editor showing a .q file with colorful syntax highlighting. XML tags in blue, attributes in purple, data bindings in orange, and SQL keywords in green.

### IntelliSense

Context-aware code completion:

- Tag names with descriptions
- Attribute names and values
- Component references
- Variable references
- Function calls

```xml
<ui:bu|
      ^-- Suggests: ui:button, ui:badge
```

```xml
<ui:button variant="|"
                    ^-- Suggests: primary, secondary, danger, success
```

### Snippets

Quick code templates for common patterns:

| Prefix | Description |
|--------|-------------|
| `qcomp` | Create component |
| `qapp` | Create application |
| `qset` | Variable declaration |
| `qloop` | Loop construct |
| `qif` | Conditional |
| `qfunc` | Function definition |
| `qquery` | Database query |
| `uiform` | Form with inputs |
| `uitable` | Data table |
| `uitabs` | Tab panel |

Example: Type `qcomp` and press Tab:

```xml
<q:component name="ComponentName" xmlns:q="https://quantum.lang/ns">
  <q:return value="" />
</q:component>
```

### Hover Information

Hover over elements to see documentation:

**Screenshot description**: Hovering over `ui:button` shows a tooltip with the component description, available attributes, and examples.

### Error Diagnostics

Real-time error detection:

- Missing required attributes
- Invalid attribute values
- Unclosed tags
- Unknown components
- Type mismatches

**Screenshot description**: Editor showing red squiggly underlines on errors, with a Problems panel listing "Missing required attribute 'name' on q:component".

### Live Preview

Preview Quantum UI in real-time:

1. Open a `.q` file
2. Run command: `Quantum: Open Preview`
3. Split editor shows live preview
4. Changes update automatically

**Screenshot description**: Split view with .q code on the left and rendered HTML preview on the right.

### Document Outline

Navigate complex files:

- View component structure
- Jump to functions
- See routes and queries
- Fold/unfold sections

**Screenshot description**: Outline panel showing hierarchical tree of q:component, q:function nodes, and ui: elements.

### Go to Definition

Navigate to component definitions:

1. Ctrl+Click on component reference
2. Or right-click > "Go to Definition"
3. Opens the component file

```xml
<!-- Ctrl+Click on "UserCard" -->
<UserCard user="{currentUser}" />
```

### Find References

Find all usages of a component or variable:

1. Right-click on identifier
2. Select "Find All References"
3. Results panel shows all usages

### Formatting

Format `.q` files:

- Auto-indent
- Tag alignment
- Attribute ordering
- Consistent spacing

Trigger: Shift+Alt+F or Format Document

### Rename Symbol

Rename components or variables:

1. Right-click on identifier
2. Select "Rename Symbol" (F2)
3. Enter new name
4. All references update

## AI Assistance

### Copilot Integration

GitHub Copilot works with Quantum files:

- Suggests component completions
- Generates function bodies
- Proposes query structures
- Helps with complex layouts

### Quantum-Specific Prompts

Use comments to guide AI suggestions:

```xml
<!-- Create a user registration form with email, password, and confirm password -->
<ui:form on-submit="handleRegister">
  <!-- AI suggests form fields here -->
</ui:form>
```

### Code Actions

AI-powered code actions:

- "Generate component from selection"
- "Extract to function"
- "Add error handling"
- "Optimize query"

## Configuration

### Extension Settings

Access via Settings > Extensions > Quantum:

```json
{
  // Enable/disable features
  "quantum.validation.enabled": true,
  "quantum.completion.enabled": true,
  "quantum.hover.enabled": true,
  "quantum.preview.enabled": true,

  // Validation options
  "quantum.validation.showWarnings": true,
  "quantum.validation.checkTypes": true,
  "quantum.validation.checkUnused": false,

  // Preview options
  "quantum.preview.autoRefresh": true,
  "quantum.preview.refreshDelay": 300,
  "quantum.preview.target": "html",

  // Formatting options
  "quantum.format.tabSize": 2,
  "quantum.format.useTabs": false,
  "quantum.format.attributeOrder": [
    "name", "id", "type", "value", "*"
  ],

  // LSP connection
  "quantum.lsp.enabled": true,
  "quantum.lsp.serverPath": "auto"
}
```

### File Associations

Associate `.q` files with Quantum language:

```json
{
  "files.associations": {
    "*.q": "quantum"
  }
}
```

### Custom Snippets

Add project-specific snippets:

```json
// .vscode/quantum.code-snippets
{
  "API Route": {
    "prefix": "qroute",
    "body": [
      "<q:route path=\"$1\" method=\"${2|GET,POST,PUT,DELETE|}\">",
      "  $0",
      "</q:route>"
    ],
    "description": "Create an API route"
  }
}
```

## Commands

Access via Command Palette (Ctrl+Shift+P):

| Command | Description |
|---------|-------------|
| `Quantum: Open Preview` | Open live preview |
| `Quantum: Run File` | Execute current file |
| `Quantum: Build` | Build current file |
| `Quantum: Start Server` | Start development server |
| `Quantum: Restart Server` | Restart development server |
| `Quantum: Show Outline` | Show document outline |
| `Quantum: Format Document` | Format current file |
| `Quantum: Validate Document` | Run validation |
| `Quantum: Clear Cache` | Clear extension cache |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+P` | Open Quantum preview |
| `F5` | Run/Debug |
| `Ctrl+Shift+B` | Build |
| `Ctrl+.` | Quick fixes |
| `F2` | Rename symbol |
| `F12` | Go to definition |
| `Shift+F12` | Find references |

Customize in Keyboard Shortcuts settings.

## Troubleshooting

### Extension not working

1. Check extension is enabled
2. Verify file has `.q` extension
3. Restart VS Code
4. Check Output panel for errors

### IntelliSense not showing

1. Wait for extension to initialize
2. Check LSP server is running
3. Try reloading window
4. Check for syntax errors

### Preview not updating

1. Check preview is connected
2. Verify auto-refresh is enabled
3. Save file to trigger refresh
4. Try closing and reopening preview

### Slow performance

1. Close unused preview panels
2. Reduce validation scope
3. Disable unused features
4. Check for large files

### LSP connection issues

1. Check LSP server path
2. Verify Python environment
3. Check Output > Quantum panel
4. Try manual server restart

## Development

### Building the Extension

```bash
# Clone repository
git clone https://github.com/quantum-lang/vscode-quantum

# Install dependencies
cd vscode-quantum
npm install

# Compile
npm run compile

# Package
npm run package
```

### Running in Development

1. Open extension folder in VS Code
2. Press F5 to launch Extension Host
3. Test in the new VS Code window

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## Related

- [LSP Server](/tools/lsp-server) - Language server details
- [CLI Commands](/tools/cli) - Command line tools
- [Hot Reload](/tools/hot-reload) - Development workflow
