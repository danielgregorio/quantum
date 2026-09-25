---
source: tools/lsp-server.md
source_hash: 2b2644e3ca9a
---

# LSP 服务器

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tools/lsp-server)为准。
:::

`quantum-lsp` 是一个面向 `.q` 文件的 Language Server Protocol 服务器：任何带有 LSP 客户端的编辑器都可以使用它。

它提供：

- 标签、属性、属性值、变量和函数的补全；
- 标签、属性和变量的悬停文档；
- 跳转到 `q:function`、`q:component` 和变量的定义；
- 查找函数、组件和变量的引用；
- 输入时的诊断；
- 格式化整个文档或选中部分；
- 文档符号（大纲）。

## 安装 {#installation}
服务器位于仓库的 `quantum-lsp/` 文件夹中；它不在 PyPI 上。从克隆中安装：

```bash
git clone https://github.com/danielgregorio/quantum
pip install ./quantum/quantum-lsp
```

```bash
quantum-lsp --version
# quantum-lsp 1.0.0
```

## 命令行 {#command-line}
```text
quantum-lsp [--stdio | --tcp] [--host HOST] [--port PORT] [--log-level LEVEL]

  --stdio           Use stdio for communication (the default)
  --tcp             Use TCP, on --host (127.0.0.1) and --port (2087)
  --log-level       DEBUG, INFO, WARNING or ERROR
  --version         Show the version
```

`python -m quantum_lsp --stdio` 效果相同，无需把脚本放在 `PATH` 中。

## 编辑器配置 {#editor-configuration}
每个编辑器需要两样东西：`.q` 文件的文件类型，以及命令 `quantum-lsp --stdio`。

### Neovim {#neovim}
使用 `nvim-lspconfig`：

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
在 `~/.config/helix/languages.toml` 中：

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
使用 `lsp-mode`：

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
在 LSP Client 设置（`lsp.json`）中：

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
[VS Code 扩展](/zh/tools/vscode-extension)不使用这个服务器：它有自己的补全、悬停提示和诊断，基于同一个标签结构构建。

## 命令 {#commands}
除了标准请求，服务器还响应两个 `workspace/executeCommand` 命令：`quantum.validateDocument` 和 `quantum.showAst`。

## 开发 {#development}
```bash
cd quantum-lsp
pip install -e ".[dev]"
pytest tests/
quantum-lsp --stdio --log-level DEBUG
```

## 相关 {#related}
- [VS Code 扩展](/zh/tools/vscode-extension) - VS Code 集成
- [CLI 命令](/zh/tools/cli) - 命令行工具
