# LSP Server

`quantum-lsp` is a Language Server Protocol server for `.q` files: any editor
with an LSP client can use it.

It provides:

- completion of tags, attributes, attribute values, variables and functions;
- hover documentation for tags, attributes and variables;
- go to definition of `q:function`, `q:component` and variables;
- find references of functions, components and variables;
- diagnostics as you type;
- formatting of a document or a selection;
- document symbols (the outline).

## Installation

The server lives in the `quantum-lsp/` folder of the repository; it is not on
PyPI. Install it from a clone:

```bash
git clone https://github.com/danielgregorio/quantum
pip install ./quantum/quantum-lsp
```

```bash
quantum-lsp --version
# quantum-lsp 1.0.0
```

## Command line

```text
quantum-lsp [--stdio | --tcp] [--host HOST] [--port PORT] [--log-level LEVEL]

  --stdio           Use stdio for communication (the default)
  --tcp             Use TCP, on --host (127.0.0.1) and --port (2087)
  --log-level       DEBUG, INFO, WARNING or ERROR
  --version         Show the version
```

`python -m quantum_lsp --stdio` is the same, without the script on `PATH`.

## Editor configuration

Each editor needs two things: a file type for `.q` files, and the command
`quantum-lsp --stdio`.

### Neovim

With `nvim-lspconfig`:

```lua
vim.filetype.add({ extension = { q = 'quantum' } })

local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

if not configs.quantum_ls then
  configs.quantum_ls = {
    default_config = {
      cmd = { 'quantum-lsp', '--stdio' },
      filetypes = { 'quantum' },
      root_dir = lspconfig.util.root_pattern('quantum.config.yaml', '.git'),
    },
  }
end

lspconfig.quantum_ls.setup({})
```

### Helix

In `~/.config/helix/languages.toml`:

```toml
[language-server.quantum-lsp]
command = "quantum-lsp"
args = ["--stdio"]

[[language]]
name = "quantum"
scope = "source.quantum"
file-types = ["q"]
roots = ["quantum.config.yaml"]
comment-token = "<!--"
language-servers = ["quantum-lsp"]
```

### Emacs

With `lsp-mode`:

```elisp
(define-derived-mode quantum-mode nxml-mode "Quantum"
  "Major mode for Quantum .q files.")
(add-to-list 'auto-mode-alist '("\\.q\\'" . quantum-mode))

(with-eval-after-load 'lsp-mode
  (add-to-list 'lsp-language-id-configuration '(quantum-mode . "quantum"))
  (lsp-register-client
   (make-lsp-client
    :new-connection (lsp-stdio-connection '("quantum-lsp" "--stdio"))
    :major-modes '(quantum-mode)
    :server-id 'quantum-ls)))

(add-hook 'quantum-mode-hook #'lsp)
```

### Kate

In the LSP Client settings (`lsp.json`):

```json
{
  "servers": {
    "quantum": {
      "command": ["quantum-lsp", "--stdio"],
      "highlightingModeRegex": "^XML$",
      "rootIndicationFileNames": ["quantum.config.yaml", ".git"]
    }
  }
}
```

### VS Code

The [VS Code extension](/tools/vscode-extension) does not use this server: it
has its own completion, hover and diagnostics, built from the same tag schema.

## Commands

Besides the standard requests, the server answers two `workspace/executeCommand`
commands: `quantum.validateDocument` and `quantum.showAst`.

## Development

```bash
cd quantum-lsp
pip install -e ".[dev]"
pytest tests/
quantum-lsp --stdio --log-level DEBUG
```

## Related

- [VS Code Extension](/tools/vscode-extension) - VS Code integration
- [CLI Commands](/tools/cli) - Command line tools
