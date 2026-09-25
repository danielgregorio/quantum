---
source: targets/desktop.md
source_hash: 27a8d69fc37c
---

# 桌面（`quantum desktop`）

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/targets/desktop)为准。
:::

`quantum desktop` 在一个原生窗口中打开你的应用。它在一个空闲的本地端口（`127.0.0.1`）上启动应用的服务器，
并在其上打开一个 [pywebview](https://pywebview.flowrl.com/) 窗口：这个窗口是一个没有浏览器外框的浏览器，
所以页面、`q:action`、会话和响应式布局与 Web 上完全相同。关闭窗口就会停止服务器。

```bash
pip install "quantum-framework[desktop]"

quantum desktop                      # the home page
quantum desktop /reports             # another page
quantum desktop --width 800 --height 600
quantum desktop --config other.config.yaml
```

没有安装 `[desktop]` 可选依赖时，命令会说明需要安装什么，而不是以导入错误失败。

窗口标题跟随页面：第一个 `ui:window` 的 `title`，否则是组件的名字——与浏览器标签页和 `quantum console` 显示的标题相同。

平台说明（来自 pywebview）：

- **Windows**：使用 Edge WebView2，Windows 10/11 已自带。
- **macOS**：使用 WebKit，无需安装。
- **Linux**：需要 GTK/WebKit，例如 `sudo apt install python3-gi gir1.2-webkit2-4.1`。

## 编写页面，而不是桌面应用 {#write-pages-not-a-desktop-app}
一个界面没有单独的"桌面版"。用 `ui:*` 元素把页面写一次——见[一个应用，多种界面](/zh/guide/ui)——然后用
`quantum start`、`quantum console` 或 `quantum desktop` 打开它。

## `--target desktop` 怎么了 {#what-happened-to-target-desktop}
在 0.15 之前，`quantum run app.q --target desktop` 会生成一个带有 JavaScript 桥的 Python 文件，把 `q:set` 和
`q:function` 翻译成它自己的响应式状态。那是语言的第二套实现，而且与第一套不一致。它在 0.16 中被移除（SPEC `UI-8`）；
用它构建会报错，并指向 `quantum desktop`。
