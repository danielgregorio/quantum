---
order: 1
title: "用 quantum test 写第一个测试"
description: "在 Quantum 本身中测试一个页面及其动作——访问、提交，检查提示消息、数据表和字段错误。"
source: cookbook/testing/first-test.md
source_hash: 0285b0b6d11f
---

# 用 `quantum test` 写第一个测试

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/testing/first-test)为准。
:::

**任务：** 检查一个页面列出了数据库中的内容、它的动作保存了一行并告知结果，
并且拒绝错误的输入——不用写 Python。

一个小应用：一张数据表、一个列出它的页面，以及一个向它添加数据的动作。

<<< @/../examples/cookbook/testing/first-test/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/first-test/migrations/V001_notes.sql{sql}

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

测试就在它旁边的 `tests/` 中。每个 `q:test` 都从一个根据 `migrations/`
新建的数据库开始，所以它们互不依赖：

<<< @/../examples/cookbook/testing/first-test/tests/notes.test.q{xml}

在应用的文件夹中运行它们：

```bash
quantum test
```

<<< @/../examples/cookbook/testing/first-test/output/test-report.txt{text}

`test:visit` 打开页面；`test:submit` 提交一个动作，其他属性作为它的字段；
`test:expect` 检查发生了什么——状态码、重定向和提示消息（flash）、页面上的一段文本、
数据表中的行，或者输入被拒绝的字段。完整的词汇见
[Testing an App](../../../guide/testing.md) 指南（英文）。

*已测试：* 本页导入了 `examples/cookbook/testing/first-test/` 中的文件，
上面的结果就是运行它们得到的报告。
