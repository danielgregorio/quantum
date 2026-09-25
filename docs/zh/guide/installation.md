---
source: guide/installation.md
source_hash: aac979eb127d
---

# 安装

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/installation)为准。
:::

## 环境要求

- **Python 3.12+**
- **pip**

## 安装

```bash
pip install quantum-framework
```

这会安装 `quantum` 命令和 `quantum` Python 包。检查一下：

```bash
quantum --version
```

```
quantum 1.0.0
```

::: tip 使用虚拟环境
先运行 `python -m venv .venv`，然后在 `pip install` 之前激活它（`source .venv/bin/activate`，
Windows 上是 `.venv\Scripts\activate`）。
:::

### 可选依赖

基础安装包含组件、Web 服务器、SQLite 查询和终端目标。其他功能都是可选依赖（extra）：

| Extra | 安装 | 增加 |
|-------|---------|------|
| `db` | `pip install "quantum-framework[db]"` | `q:query` 使用的 PostgreSQL 和 MySQL 驱动 |
| `rag` | `pip install "quantum-framework[rag]"` | `q:knowledge` / RAG 查询使用的向量存储 |
| `jobs` | `pip install "quantum-framework[jobs]"` | `q:schedule` 背后的调度器 |
| `websocket` | `pip install "quantum-framework[websocket]"` | `q:websocket` 背后的传输层 |

可选依赖可以组合：`pip install "quantum-framework[db,jobs]"`。

**桌面**目标还需要 `pip install pywebview`（在 Linux 上，pywebview 有它自己的系统依赖——见它的文档）。

AI 标签（`q:llm`、`q:knowledge`、`q:agent`）会连接一个 [Ollama](https://ollama.com)
服务器——默认是 `http://localhost:11434`，除非 `QUANTUM_LLM_BASE_URL` 另有设置。

哪些部分是稳定的、哪些是实验性的，见[稳定性](/zh/stability/)。

## 验证

创建 `hello.q`：

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

**输出：** `Hello World!`

```bash
quantum run hello.q
```

```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

### Web 服务器

把组件放在 `components/` 文件夹里，然后在包含它的文件夹中启动服务器：

```
myapp/
└── components/
    └── index.q      # served at /
```

```bash
quantum start               # http://localhost:8080
quantum start --port 9000   # another port
quantum stop                # stops the server started above
```

`components/orders.q` 对应 `/orders`，依此类推。

## 配置

设置放在 `quantum.config.yaml` 中，与 `components/` 同级。`q:query` 使用的数据源：

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

通过引用环境变量，把密钥留在文件之外。`${NAME:-default}` 在变量不存在时使用默认值，
`$$` 表示字面的 `$`：

```yaml
datasources:
  db:
    driver: postgres
    host: ${DB_HOST:-localhost}
    database: app
    username: app
    password: ${DB_PASSWORD}
```

如果没有设置 `DB_PASSWORD`，Quantum 会拒绝启动，并说明是哪个变量、哪项设置。

## 从源码安装

参与 Quantum 本身的开发：

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
pip install -e ".[dev,db,jobs,websocket]" -r quantum_admin/backend/requirements.txt
pytest
```

文档站点在仓库根目录构建：

```bash
npm ci
npm run docs:dev
```

[CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md)
介绍了架构以及如何添加一个标签。

## 常见问题

**`quantum: command not found`**——运行 `pip install` 的环境没有激活，或者它的
`Scripts`/`bin` 文件夹不在 `PATH` 中。`python -m quantum.cli.runner --version` 在两种情况下都能用。

**XML 解析错误**——`.q` 文件是 XML：每个标签都要闭合，属性要加引号，文本中的 `<`、`>`、`&`
要写成 `&lt;`、`&gt;`、`&amp;`。错误信息会指出行号和列号。

**`Port 8080 already in use`**——另一个服务器正在运行。使用 `quantum stop`，或者
`quantum start --port <其他端口>`。

**`Not stopping PID …`**——`quantum stop` 找到了一个 `.quantum.pid`，但其中的进程并不是写下它的那个服务器
（服务器退出时没有清理，它的进程号现在属于另一个程序）。它不会结束任何进程，并删除这个过期文件；
如果还有 Quantum 服务器在运行，请手动停止它。

## 下一步

- [快速开始](/zh/guide/quick-start)——构建你的第一个应用
- [组件](/guide/components)——组件系统（英文）
- [帮助与 Issue](https://github.com/danielgregorio/quantum/issues)
