---
order: 1
title: "第一个页面，以及第二个"
description: "components/ 中的每个文件都是一个页面，有自己的 URL；没有对应文件的 URL 返回 404。"
source: cookbook/basics/first-page.md
source_hash: 2f3e3e2fd454
---

# 第一个页面，以及第二个

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/first-page)为准。
:::

**任务：** 提供两个互相链接的页面。

<<< @/../examples/cookbook/basics/first-page/quantum.config.yaml{yaml}

`components/` 中的文件就是一个页面，URL 就是它的路径：
`components/index.q` 响应 `/`，`components/about.q` 响应 `/about`。
在包含 `quantum.config.yaml` 的文件夹中用 `quantum start` 启动服务器。

<<< @/../examples/cookbook/basics/first-page/components/index.q{xml}

<<< @/../examples/cookbook/basics/first-page/components/about.q{xml}

没有对应文件的 URL 返回 `404`：

<<< @/../examples/cookbook/basics/first-page/tests/pages.test.q{xml}

<<< @/../examples/cookbook/basics/first-page/output/test-report.txt{text}

参见 [ROUTE-1](../../../reference/spec.md#ROUTE-1)。
