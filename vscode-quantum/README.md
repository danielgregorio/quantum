# Quantum Language Support for VS Code

Comprehensive language support for the Quantum Framework in Visual Studio Code.

## Features

### Phase 1: Language Basics

- **Syntax Highlighting** - Full syntax highlighting for `.q` files with support for:
  - Quantum core tags (`q:component`, `q:set`, `q:loop`, `q:if`, etc.)
  - UI Engine tags (`ui:window`, `ui:button`, `ui:input`, etc.)
  - Game Engine tags (`qg:scene`, `qg:sprite`, etc.)
  - Terminal UI tags (`qt:screen`, `qt:widget`, etc.)
  - Testing tags (`qtest:suite`, `qtest:test`, etc.)
  - Component calls (PascalCase tags)
  - Databinding expressions (`{variable}`)
  - Attributes and values

- **Code Snippets** - Quick insertion of common patterns:
  - `qcomp` - Create a component
  - `qset` - Set a variable
  - `qloop` - Create a loop
  - `qif` - Conditional block
  - `qfunc` - Define a function
  - `qquery` - Database query
  - `uiwin` - UI Window
  - `uibtn` - UI Button
  - `uiinput` - UI Input
  - And 50+ more snippets

- **Auto-close Tags** - Automatic closing of XML-style tags
- **Bracket Matching** - Matching of `{}` in databinding expressions

### Phase 2: Intelligence

- **IntelliSense/Autocomplete**
  - Tag name suggestions with descriptions
  - Context-aware attribute suggestions
  - Attribute value completion (enums, booleans)
  - Variable/function references in databinding
  - Closing tag suggestions

- **Go to Definition** (F12)
  - Jump to `q:function` definitions
  - Jump to `q:component` definitions
  - Jump to variable declarations (`q:set`)
  - Navigate to imported components

- **Hover Documentation**
  - Rich documentation for tags
  - Attribute descriptions with types and values
  - Variable and function type info

- **Diagnostics/Linting**
  - Missing required attributes
  - Invalid attribute values
  - Unclosed tags
  - Undefined variable warnings
  - Duplicate function names
  - PascalCase component name validation

- **Code Actions/Quick Fixes**
  - Add missing required attributes
  - Fix invalid boolean values

## Installation

### From VSIX (Local)

1. Build the extension:
   ```bash
   cd vscode-quantum
   npm install
   npm run compile
   npx vsce package
   ```

2. Install in VS Code:
   - Open VS Code
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Install from VSIX"
   - Select the generated `.vsix` file

### From Source (Development)

1. Clone and install:
   ```bash
   cd vscode-quantum
   npm install
   npm run compile
   ```

2. Press F5 in VS Code to launch Extension Development Host

## Usage

### Snippets

Type any of the snippet prefixes and press Tab:

| Prefix | Description |
|--------|-------------|
| `qcomp` | Component definition |
| `qset` | Set variable |
| `qloop` | Range loop |
| `qloopa` | Array loop |
| `qif` | If condition |
| `qfunc` | Function definition |
| `qquery` | Database query |
| `uiwin` | UI Window |
| `uivbox` | Vertical container |
| `uihbox` | Horizontal container |
| `uibtn` | Button widget |
| `uiinput` | Input field |
| `uiform` | Form with validation |
| `uitable` | Data table |
| `uicard` | Card component |
| `uimodal` | Modal dialog |

### Commands

Access via Command Palette (`Ctrl+Shift+P`):

- **Quantum: Run Quantum File** - Execute the current `.q` file
- **Quantum: Start Development Server** - Start the Quantum server
- **Quantum: Validate** - Validate the current document
- **Quantum: Lookup Documentation** - Open docs for element under cursor

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+R` | Run Quantum file |
| `Ctrl+K V` | Open preview (coming soon) |
| `Ctrl+Shift+D` | Lookup documentation |
| `F12` | Go to definition |
| `Shift+F12` | Find all references |

## Configuration

Configure the extension in VS Code settings:

```json
{
  "quantum.validation.enabled": true,
  "quantum.validation.showWarnings": true,
  "quantum.completion.enabled": true,
  "quantum.hover.enabled": true,
  "quantum.pythonPath": "python",
  "quantum.frameworkPath": "",
  "quantum.serverPort": 8080
}
```

## Supported Tags

### Quantum Core (`q:`)

| Tag | Description |
|-----|-------------|
| `q:component` | Component definition |
| `q:application` | Application root |
| `q:set` | Variable assignment |
| `q:loop` | Iteration |
| `q:if` / `q:else` / `q:elseif` | Conditionals |
| `q:function` | Function definition |
| `q:param` | Parameter definition |
| `q:query` | Database query |
| `q:invoke` | HTTP/function call |
| `q:action` | Form action handler |
| `q:import` | Component import |
| `q:slot` | Content projection |
| `q:llm` | LLM invocation |
| `q:mail` | Email sending |

### UI Engine (`ui:`)

| Tag | Description |
|-----|-------------|
| `ui:window` | Top-level container |
| `ui:hbox` / `ui:vbox` | Flex containers |
| `ui:panel` | Bordered panel |
| `ui:grid` | CSS Grid layout |
| `ui:button` | Clickable button |
| `ui:input` | Text input |
| `ui:select` | Dropdown select |
| `ui:table` | Data table |
| `ui:list` | Repeating list |
| `ui:card` | Card component |
| `ui:modal` | Modal dialog |
| `ui:form` | Form with validation |
| `ui:chart` | Simple charts |

## Requirements

- VS Code 1.74.0 or higher
- Quantum Framework (for running `.q` files)
- Python 3.8+ (for Quantum runtime)

## Known Issues

- Preview panel is under development
- Some advanced diagnostic rules may have false positives

## Release Notes

### 1.0.0

- Initial release
- Phase 1: Syntax highlighting, snippets, auto-close
- Phase 2: IntelliSense, hover, go to definition, diagnostics

## Contributing

Contributions are welcome! Please see the [Quantum Framework repository](https://github.com/quantum-framework/quantum) for guidelines.

## License

MIT License - see LICENSE file for details.
