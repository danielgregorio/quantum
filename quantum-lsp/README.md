# Quantum LSP

Language Server Protocol implementation for the Quantum Framework.

## Features

- **Autocompletion**: Tag names, attributes, values, variables, and functions
- **Hover**: Documentation for tags, attributes, and variables
- **Go to Definition**: Navigate to q:function, q:component, and variable definitions
- **Find References**: Find all usages of functions, components, and variables
- **Diagnostics**: Real-time linting with validation and error detection
- **Formatting**: Code formatting for .q files
- **Document Symbols**: Outline view with all defined symbols

## Installation

```bash
pip install quantum-lsp
```

Or install from source:

```bash
cd quantum-lsp
pip install -e .
```

## Usage

### Command Line

```bash
# Start the server in stdio mode
quantum-lsp --stdio

# Or use Python module
python -m quantum_lsp --stdio
```

## Editor Configuration

### VS Code

Create or update `.vscode/settings.json`:

```json
{
  "quantum.lsp.enabled": true,
  "quantum.lsp.serverPath": "quantum-lsp",
  "quantum.lsp.args": ["--stdio"],
  "[quantum]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "quantum.quantum-vscode"
  }
}
```

For a generic LSP client extension, configure:

```json
{
  "lsp": {
    "quantum": {
      "command": "quantum-lsp",
      "args": ["--stdio"],
      "filetypes": ["quantum"],
      "rootPatterns": ["pyproject.toml", ".git"]
    }
  }
}
```

### Neovim (lspconfig)

Add to your `init.lua`:

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

-- Define the Quantum LSP configuration
if not configs.quantum_lsp then
  configs.quantum_lsp = {
    default_config = {
      cmd = { 'quantum-lsp', '--stdio' },
      filetypes = { 'quantum', 'q' },
      root_dir = lspconfig.util.root_pattern('pyproject.toml', '.git'),
      settings = {},
    },
    docs = {
      description = [[
        Language Server for Quantum Framework (.q files)
      ]],
    },
  }
end

-- Enable the server
lspconfig.quantum_lsp.setup({
  on_attach = function(client, bufnr)
    -- Your on_attach configuration
  end,
  capabilities = require('cmp_nvim_lsp').default_capabilities(),
})

-- Register .q file type
vim.filetype.add({
  extension = {
    q = 'quantum',
  },
})
```

### Sublime Text (LSP)

Install the LSP package, then add to `LSP.sublime-settings`:

```json
{
  "clients": {
    "quantum-lsp": {
      "enabled": true,
      "command": ["quantum-lsp", "--stdio"],
      "selector": "source.quantum",
      "schemes": ["file"],
      "settings": {}
    }
  }
}
```

Also create a syntax file `Quantum.sublime-syntax`:

```yaml
%YAML 1.2
---
name: Quantum
file_extensions:
  - q
scope: source.quantum
contexts:
  main:
    - include: tags
  tags:
    - match: '</?q:'
      scope: punctuation.definition.tag.quantum
```

### Helix

Add to `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "quantum"
scope = "source.quantum"
injection-regex = "quantum"
file-types = ["q"]
roots = ["pyproject.toml", ".git"]
comment-token = "<!--"
language-servers = ["quantum-lsp"]
indent = { tab-width = 2, unit = "  " }

[language-server.quantum-lsp]
command = "quantum-lsp"
args = ["--stdio"]
```

### Zed

Add to your Zed settings (Settings > Open Settings):

```json
{
  "lsp": {
    "quantum-lsp": {
      "binary": {
        "path": "quantum-lsp",
        "arguments": ["--stdio"]
      }
    }
  },
  "languages": {
    "Quantum": {
      "language_servers": ["quantum-lsp"]
    }
  }
}
```

### Emacs (lsp-mode)

Add to your Emacs configuration:

```elisp
(require 'lsp-mode)

;; Register Quantum file type
(add-to-list 'auto-mode-alist '("\\.q\\'" . nxml-mode))

;; Configure Quantum LSP
(lsp-register-client
 (make-lsp-client
  :new-connection (lsp-stdio-connection '("quantum-lsp" "--stdio"))
  :major-modes '(nxml-mode)
  :server-id 'quantum-lsp
  :activation-fn (lsp-activate-on "quantum")))

(add-hook 'nxml-mode-hook
          (lambda ()
            (when (string-match-p "\\.q\\'" (buffer-file-name))
              (lsp))))
```

### Vim (vim-lsp)

Add to your `.vimrc`:

```vim
if executable('quantum-lsp')
  au User lsp_setup call lsp#register_server({
    \ 'name': 'quantum-lsp',
    \ 'cmd': {server_info->['quantum-lsp', '--stdio']},
    \ 'allowlist': ['quantum'],
    \ })
endif

" Register .q files
au BufRead,BufNewFile *.q setfiletype quantum
```

## Development

```bash
# Clone the repository
git clone https://github.com/quantum-framework/quantum-lsp.git
cd quantum-lsp

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run the server for testing
python -m quantum_lsp --stdio
```

## License

MIT License - see LICENSE file for details.
