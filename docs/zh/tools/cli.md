---
source: tools/cli.md
source_hash: 12afaadf1bf6
---

# CLI 命令

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tools/cli)为准。
:::

`pip install quantum-framework` 会安装 `quantum` 命令。

```bash
quantum <command>
python -m quantum.cli.runner <command>   # the same, without the script on PATH
```

每个命令都接受 `-h` / `--help`。本页介绍日常使用的命令；由代码生成的[命令行参考](/reference/cli)列出了所有命令和选项。

## 命令概览 {#commands-overview}
| 命令 | 说明 |
|---------|-------------|
| `run` | 执行一个 `.q` 文件 |
| `start` | 提供应用的页面 |
| `stop` | 停止由 `quantum start` 启动的服务器 |
| `console` | 在终端中显示应用的页面 |
| `desktop` | 在桌面窗口中显示应用的页面 |
| `check` | 页面能解析、SQL 能编译、查询字段存在 |
| `test` | 运行应用的 `*.test.q` 测试 |
| `migrate` | 应用、回滚和规划数据库迁移 |

## quantum run {#quantum-run}
执行一个 Quantum 文件（`.q`）。

```bash
quantum run <file.q> [options]
```

| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `--debug` | 打印解析和运行的内容 | 关闭 |
| `--config` | 配置文件路径 | `quantum.config.yaml` |
| `--target` | 独立 UI 构建（`type="ui"`）：`html`、`textual`（仅布局）、`mobile`（实验室） | `html` |

```bash
$ quantum run hello.q
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!

$ quantum run hello.q --debug
[DEBUG] Parsing file: hello.q
[DEBUG] AST generated: ComponentNode
[DEBUG] Validating AST...
[EXEC] Executing component: HelloWorld
   Type: pure
   Params: 0
   Returns: 1
[SUCCESS] Result: Hello World!
```

`run` 的行为取决于文件：

| 文件 | 行为 |
|------|----------|
| `q:component` | 执行它并打印结果 |
| `q:application type="ui"` | 构建独立 UI（实验层） |
| `q:application type="terminal"` | 构建终端应用（实验层） |
| `q:application type="game"` | 构建游戏（实验室） |
| `q:job` | 运行该任务（实验层） |

Web 应用不是 `q:application`：它是 `components/` 中的页面，由 `quantum start` 提供（APP-1）。

不存在、无法解析或运行失败的文件会以 `1` 退出。

## quantum start {#quantum-start}
在 `quantum.config.yaml` 中配置的端口（默认 8080）上提供 `components/` 中的页面。

```bash
quantum start                  # in the application's folder
quantum start --port 3000
quantum start --hot-reload     # reload the open pages on every save
```

调试模式——[/_dev 面板](/zh/tools/dev-panel)和详细的[错误页面](/zh/tools/error-pages)——是 `quantum.config.yaml` 中的 `server.debug: true`。
`--debug` 参数只在服务器启动失败时打印 traceback。另见[热重载](/zh/tools/hot-reload)。

## quantum stop {#quantum-stop}
停止 `quantum start` 在当前文件夹启动的服务器（它把进程记录在 `.quantum.pid` 中）。
无法确定是那个服务器的进程不会被结束：命令会说明情况并以 `1` 退出（RUN-3）。

## quantum console {#quantum-console}
在终端中显示同样的页面：

```bash
quantum console              # the home page
quantum console /reports     # another page
quantum console --config other.config.yaml
```

## quantum desktop {#quantum-desktop}
在桌面窗口中显示同样的页面（[桌面](/zh/targets/desktop)）：

```bash
quantum desktop
quantum desktop /reports --width 800 --height 600
```

## quantum check {#quantum-check}
解析每个页面，并针对数据库编译每个查询，但不运行它们（[quantum check](/zh/tools/check)）：

```bash
quantum check
quantum check --config other.config.yaml
```

## quantum test {#quantum-test}
运行应用的 `*.test.q` 文件（[测试应用](/zh/guide/testing)）：

```bash
quantum test                   # every *.test.q under the current folder
quantum test tests/            # a folder, or files
```

测试失败时以 `1` 退出，因此适合在 CI 中使用。

## quantum migrate {#quantum-migrate}
`migrations/` 中的数据库迁移（[数据库查询](/zh/guide/query)）：

```bash
quantum migrate status
quantum migrate up
quantum migrate down           # the last one
quantum migrate create add_due_date
quantum migrate plan           # compare schema.sql with the migrations
```

## 其他命令 {#other-commands}
`quantum admin` 启动 [Quantum Admin](/zh/guide/admin)。`quantum jobs` 和 `quantum mq` 属于任务和消息，它们是实验层（见[稳定性](/zh/stability/)）。
`quantum pkg` 打包和安装组件文件夹，但页面目前还不能从已安装的包中导入组件：`q:import from=` 是 `paths.components` 下的一个文件夹。
它们的选项在[命令行参考](/reference/cli)中。

## 相关 {#related}
- [热重载](/zh/tools/hot-reload) - `quantum start --hot-reload`
- [VS Code 扩展](/zh/tools/vscode-extension) - 编辑器支持
- [项目结构](/zh/guide/project-structure) - 文件组织
