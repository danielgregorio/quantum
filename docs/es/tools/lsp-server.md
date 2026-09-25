---
source: tools/lsp-server.md
source_hash: 2b2644e3ca9a
---

# Servidor LSP

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tools/lsp-server).
:::

`quantum-lsp` es un servidor del Language Server Protocol para archivos `.q`:
cualquier editor con un cliente LSP puede usarlo.

Ofrece:

- autocompletado de etiquetas, atributos, valores de atributos, variables y funciones;
- documentación al pasar el cursor sobre etiquetas, atributos y variables;
- ir a la definición de `q:function`, `q:component` y variables;
- buscar referencias de funciones, componentes y variables;
- diagnósticos mientras escribes;
- formato de un documento o de una selección;
- símbolos del documento (el esquema).

## Instalación {#installation}
El servidor vive en la carpeta `quantum-lsp/` del repositorio; no está en PyPI.
Instálalo desde un clon:

```bash
git clone https://github.com/danielgregorio/quantum
pip install ./quantum/quantum-lsp
```

```bash
quantum-lsp --version
# quantum-lsp 1.0.0
```

## Línea de comandos {#command-line}
```text
quantum-lsp [--stdio | --tcp] [--host HOST] [--port PORT] [--log-level LEVEL]

  --stdio           Use stdio for communication (the default)
  --tcp             Use TCP, on --host (127.0.0.1) and --port (2087)
  --log-level       DEBUG, INFO, WARNING or ERROR
  --version         Show the version
```

`python -m quantum_lsp --stdio` es lo mismo, sin el script en el `PATH`.

## Configuración del editor {#editor-configuration}
Cada editor necesita dos cosas: un tipo de archivo para los archivos `.q`, y el
comando `quantum-lsp --stdio`.

### Neovim {#neovim}
Con `nvim-lspconfig`:

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

### Helix {#helix}
En `~/.config/helix/languages.toml`:

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

### Emacs {#emacs}
Con `lsp-mode`:

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

### Kate {#kate}
En la configuración del LSP Client (`lsp.json`):

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

### VS Code {#vs-code}
La [extensión de VS Code](/es/tools/vscode-extension) no usa este servidor: tiene
su propio autocompletado, hover y diagnósticos, construidos a partir del mismo
esquema de etiquetas.

## Comandos {#commands}
Además de las solicitudes estándar, el servidor responde a dos comandos
`workspace/executeCommand`: `quantum.validateDocument` y `quantum.showAst`.

## Desarrollo {#development}
```bash
cd quantum-lsp
pip install -e ".[dev]"
pytest tests/
quantum-lsp --stdio --log-level DEBUG
```

## Relacionado {#related}
- [Extensión de VS Code](/es/tools/vscode-extension) - Integración con VS Code
- [Comandos de la CLI](/es/tools/cli) - Herramientas de línea de comandos
