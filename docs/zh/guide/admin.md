---
source: guide/admin.md
source_hash: 94cd00f82477
---
# Quantum Admin

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/admin)为准。
:::

Admin 是一个 Quantum 应用，用来管理某个文件夹中的应用：列出并创建应用，启动和停止它们的服务器，编辑它们的配置和连接器，浏览它们的组件并运行它们的测试。它的界面是基于[声明式服务](/zh/guide/services)的 `.q` 文件。

## 安装并启动 {#install-and-start}

```bash
pip install "quantum-framework[admin]"
cd my-workspace
quantum admin
```

打开 `http://127.0.0.1:8090/admin`，以 `admin` 身份登录。没有设置 `ADMIN_PASSWORD` 时，Admin 启动时会生成一个密码并打印出来；每次重启都会变化。设置它可以得到固定的登录密码：

```bash
ADMIN_PASSWORD="a long password" quantum admin
```

Admin 只监听 `127.0.0.1`。

## 数据存放在哪里 {#where-the-data-goes}

| 选项 | 默认值 | 含义 |
|--------|---------|------------|
| `--data` | `./.quantum-admin` | Admin 的数据库、它的设置（连接器、全局设置、进程 PID）、会话密钥，以及生成的 `quantum.config.yaml` |
| `--root` | 当前文件夹 | 应用路径相对的文件夹；**Sync** 会把 `<root>/projects` 下的每个文件夹注册进来 |
| `--port` | `8090` | |

生成的配置在每次启动时都会重写；请修改选项，而不是这个文件。不要把数据文件夹放进版本控制：里面有密钥。

没有安装可选依赖（extra）`[admin]` 时，命令会停止并说明需要安装什么。
