---
source: tools/lsp-server.md
source_hash: 2b2644e3ca9a
---

# Servidor LSP

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tools/lsp-server).
:::

O `quantum-lsp` é um servidor do Language Server Protocol para arquivos `.q`:
qualquer editor com um cliente LSP pode usá-lo.

Ele oferece:

- autocompletar de tags, atributos, valores de atributos, variáveis e funções;
- documentação ao passar o mouse sobre tags, atributos e variáveis;
- ir para a definição de `q:function`, `q:component` e variáveis;
- encontrar referências de funções, componentes e variáveis;
- diagnósticos enquanto você digita;
- formatação de um documento ou de uma seleção;
- símbolos do documento (o outline).

## Instalação {#installation}
O servidor fica na pasta `quantum-lsp/` do repositório; ele não está no PyPI.
Instale-o a partir de um clone:

```bash
git clone https://github.com/danielgregorio/quantum
pip install ./quantum/quantum-lsp
```

```bash
quantum-lsp --version
# quantum-lsp 1.0.0
```

## Linha de comando {#command-line}
```text
quantum-lsp [--stdio | --tcp] [--host HOST] [--port PORT] [--log-level LEVEL]

  --stdio           Use stdio for communication (the default)
  --tcp             Use TCP, on --host (127.0.0.1) and --port (2087)
  --log-level       DEBUG, INFO, WARNING or ERROR
  --version         Show the version
```

`python -m quantum_lsp --stdio` é o mesmo, sem o script no `PATH`.

## Configuração do editor {#editor-configuration}
Cada editor precisa de duas coisas: um tipo de arquivo para os arquivos `.q`, e o
comando `quantum-lsp --stdio`.

### Neovim {#neovim}
Com o `nvim-lspconfig`:

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
Em `~/.config/helix/languages.toml`:

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
Com o `lsp-mode`:

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
Nas configurações do LSP Client (`lsp.json`):

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
A [extensão do VS Code](/pt/tools/vscode-extension) não usa este servidor: ela tem
o seu próprio autocompletar, hover e diagnósticos, construídos a partir do mesmo
esquema de tags.

## Comandos {#commands}
Além das requisições padrão, o servidor responde a dois comandos
`workspace/executeCommand`: `quantum.validateDocument` e `quantum.showAst`.

## Desenvolvimento {#development}
```bash
cd quantum-lsp
pip install -e ".[dev]"
pytest tests/
quantum-lsp --stdio --log-level DEBUG
```

## Relacionados {#related}
- [Extensão do VS Code](/pt/tools/vscode-extension) - Integração com o VS Code
- [Comandos da CLI](/pt/tools/cli) - Ferramentas de linha de comando
