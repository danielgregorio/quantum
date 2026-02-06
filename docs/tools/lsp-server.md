# LSP Server

The Quantum Language Server Protocol (LSP) server provides IDE features for any editor that supports LSP.

## Overview

The LSP server enables:

- Code completion
- Hover documentation
- Go to definition
- Find references
- Diagnostics (errors/warnings)
- Formatting
- Rename refactoring
- Code actions

## Installation

### Using pip

```bash
pip install quantum-lsp
```

### From Source

```bash
# Clone repository
git clone https://github.com/quantum-lang/quantum
cd quantum

# Install with LSP support
pip install -e ".[lsp]"
```

### Verify Installation

```bash
quantum-lsp --version
# Quantum LSP Server v1.0.0

# Test connection
quantum-lsp --stdio
```

## Editor Configuration

### Neovim

Using `nvim-lspconfig`:

```lua
-- ~/.config/nvim/lua/lsp/quantum.lua

local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

-- Define Quantum language server
if not configs.quantum_ls then
  configs.quantum_ls = {
    default_config = {
      cmd = { 'quantum-lsp', '--stdio' },
      filetypes = { 'quantum' },
      root_dir = lspconfig.util.root_pattern('quantum.config.yaml', '.git'),
      settings = {},
    },
  }
end

-- Enable the server
lspconfig.quantum_ls.setup({
  on_attach = function(client, bufnr)
    -- Keymaps
    local opts = { buffer = bufnr }
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
    vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
    vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
    vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, opts)
  end,
  capabilities = require('cmp_nvim_lsp').default_capabilities(),
})
```

File type detection:

```lua
-- ~/.config/nvim/ftdetect/quantum.lua
vim.filetype.add({
  extension = {
    q = 'quantum',
  },
})
```

Syntax highlighting (TreeSitter or basic):

```lua
-- ~/.config/nvim/syntax/quantum.vim
if exists("b:current_syntax")
  finish
endif

" Use XML highlighting as base
runtime! syntax/xml.vim

" Quantum-specific highlights
syn match quantumBinding /{[^}]*}/ containedin=xmlString
syn match quantumTag /\v\<\/?q:[a-z]+/ containedin=xmlTag
syn match quantumUITag /\v\<\/?ui:[a-z]+/ containedin=xmlTag

hi def link quantumBinding Special
hi def link quantumTag Keyword
hi def link quantumUITag Type

let b:current_syntax = "quantum"
```

### Sublime Text

Install LSP package first:

1. Install Package Control
2. Install "LSP" package
3. Install "LSP-quantum" (or configure manually)

Manual configuration:

```json
// Preferences > Package Settings > LSP > Settings

{
  "clients": {
    "quantum": {
      "enabled": true,
      "command": ["quantum-lsp", "--stdio"],
      "selector": "source.quantum",
      "languages": [
        {
          "languageId": "quantum",
          "scopes": ["source.quantum"],
          "syntaxes": ["Packages/Quantum/Quantum.sublime-syntax"]
        }
      ]
    }
  }
}
```

Create syntax file:

```yaml
# Packages/User/Quantum.sublime-syntax
%YAML 1.2
---
name: Quantum
file_extensions: [q]
scope: source.quantum

contexts:
  main:
    - include: xml
    - include: quantum-tags
    - include: bindings

  quantum-tags:
    - match: '</?q:'
      scope: keyword.control.quantum
    - match: '</?ui:'
      scope: entity.name.tag.quantum

  bindings:
    - match: '\{[^}]+\}'
      scope: variable.other.quantum

  xml:
    - include: scope:text.xml
```

### Helix

Configuration in `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "quantum"
scope = "source.quantum"
injection-regex = "quantum"
file-types = ["q"]
roots = ["quantum.config.yaml"]
comment-token = "<!--"
language-server = { command = "quantum-lsp", args = ["--stdio"] }
indent = { tab-width = 2, unit = "  " }

[[grammar]]
name = "quantum"
source = { git = "https://github.com/quantum-lang/tree-sitter-quantum", rev = "main" }
```

### Emacs

Using `lsp-mode`:

```elisp
;; ~/.emacs.d/init.el or ~/.emacs

(use-package lsp-mode
  :ensure t
  :hook ((quantum-mode . lsp)))

(use-package quantum-mode
  :ensure nil
  :mode "\\.q\\'"
  :config
  (lsp-register-client
    (make-lsp-client
      :new-connection (lsp-stdio-connection '("quantum-lsp" "--stdio"))
      :major-modes '(quantum-mode)
      :server-id 'quantum-ls)))

;; Define quantum-mode (basic)
(define-derived-mode quantum-mode nxml-mode "Quantum"
  "Major mode for editing Quantum files."
  (setq-local comment-start "<!-- ")
  (setq-local comment-end " -->"))
```

### Zed

Configuration in `~/.config/zed/settings.json`:

```json
{
  "languages": {
    "Quantum": {
      "language_servers": ["quantum-lsp"]
    }
  },
  "lsp": {
    "quantum-lsp": {
      "binary": {
        "path": "quantum-lsp",
        "arguments": ["--stdio"]
      }
    }
  }
}
```

### Kate/KDevelop

Configuration in `.config/kate/lsp.json`:

```json
{
  "servers": {
    "quantum": {
      "command": ["quantum-lsp", "--stdio"],
      "filetypes": ["quantum"],
      "rootIndicators": ["quantum.config.yaml", ".git"]
    }
  }
}
```

## LSP Features

### Completion

Provides suggestions for:

- Tag names (`q:`, `ui:`)
- Attribute names
- Attribute values (enums)
- Variable references
- Component references
- Function names

```xml
<ui:button variant="|"
           ^-- CompletionList:
               - primary
               - secondary
               - danger
               - success
```

### Hover

Shows documentation on hover:

```
ui:button
---------
A clickable button component.

Attributes:
- variant: Button style (primary, secondary, danger)
- on-click: Click handler function
- disabled: Disable the button

Example:
<ui:button variant="primary" on-click="submit">
  Submit
</ui:button>
```

### Diagnostics

Reports errors and warnings:

| Severity | Example |
|----------|---------|
| Error | Missing required attribute |
| Error | Unknown tag |
| Error | Unclosed element |
| Warning | Unused variable |
| Warning | Deprecated attribute |
| Info | Performance suggestion |

### Go to Definition

Navigates to:

- Component definitions
- Function definitions
- Variable declarations
- Import sources

### Find References

Finds all usages of:

- Components
- Functions
- Variables
- Queries

### Rename

Renames across files:

- Variables
- Functions
- Components

### Formatting

Formats document according to settings:

```json
{
  "quantum.format.tabSize": 2,
  "quantum.format.insertSpaces": true,
  "quantum.format.attributesOnNewLine": false
}
```

### Code Actions

Quick fixes and refactorings:

| Action | Description |
|--------|-------------|
| Add missing attribute | Adds required attributes |
| Remove unused variable | Removes unused q:set |
| Extract component | Creates new component from selection |
| Inline component | Replaces component with its content |
| Convert to function | Extracts logic to q:function |

## Server Configuration

### Command Line Options

```bash
quantum-lsp [options]

Options:
  --stdio           Use stdio for communication (default)
  --tcp PORT        Use TCP on specified port
  --socket PATH     Use Unix socket
  --log FILE        Log to file
  --log-level LEVEL Set log level (debug, info, warn, error)
  --version         Show version
  --help            Show help
```

### Settings

Configure via LSP `workspace/configuration`:

```json
{
  "quantum": {
    "validation": {
      "enabled": true,
      "checkTypes": true,
      "checkUnused": true
    },
    "completion": {
      "snippets": true,
      "autoImport": true
    },
    "format": {
      "tabSize": 2,
      "insertSpaces": true
    },
    "diagnostics": {
      "delay": 500
    }
  }
}
```

## Troubleshooting

### Server not starting

1. Check installation: `quantum-lsp --version`
2. Verify Python path
3. Check for error output
4. Try running manually

```bash
# Debug mode
quantum-lsp --stdio --log /tmp/quantum-lsp.log --log-level debug
```

### Features not working

1. Check server is connected (hover should work)
2. Verify file type is recognized
3. Check server logs for errors
4. Restart language server

### Slow performance

1. Reduce diagnostic delay
2. Limit workspace scope
3. Disable unused features
4. Check for large files

### Completion not showing

1. Verify cursor position
2. Check for syntax errors before cursor
3. Try triggering manually (Ctrl+Space)
4. Check server logs

## Protocol Details

### Capabilities

The server advertises these capabilities:

```json
{
  "textDocumentSync": 2,
  "completionProvider": {
    "triggerCharacters": ["<", "\"", "{", ":"],
    "resolveProvider": true
  },
  "hoverProvider": true,
  "definitionProvider": true,
  "referencesProvider": true,
  "documentFormattingProvider": true,
  "renameProvider": {
    "prepareProvider": true
  },
  "codeActionProvider": true,
  "documentSymbolProvider": true,
  "workspaceSymbolProvider": true,
  "diagnosticProvider": {
    "interFileDependencies": true,
    "workspaceDiagnostics": true
  }
}
```

### Custom Methods

Extended methods for Quantum-specific features:

| Method | Description |
|--------|-------------|
| `quantum/preview` | Generate preview HTML |
| `quantum/build` | Build to target |
| `quantum/run` | Execute file |
| `quantum/getAst` | Get parsed AST |

## Development

### Building from Source

```bash
cd quantum
pip install -e ".[lsp,dev]"

# Run tests
pytest tests/lsp/

# Run server in debug mode
quantum-lsp --stdio --log-level debug
```

### Contributing

1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## Related

- [VS Code Extension](/tools/vscode-extension) - VS Code integration
- [CLI Commands](/tools/cli) - Command line tools
- [Hot Reload](/tools/hot-reload) - Development workflow
