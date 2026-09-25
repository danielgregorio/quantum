---
order: 2
title: "用 test:given 准备测试数据"
description: "用 test:given 把测试需要的行放进它的全新数据库，用 test:as 让用户登录。"
source: cookbook/testing/test-data.md
source_hash: 96b9d6f6e931
---

# 用 `test:given` 准备测试数据

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/testing/test-data)为准。
:::

**任务：** 测试一个依赖数据和访问者身份的页面——不需要夹具（fixtures）文件，也不需要密码。

这个页面列出已登录用户未完成的任务：

<<< @/../examples/cookbook/testing/test-data/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/test-data/migrations/V001_tasks.sql{sql}

<<< @/../examples/cookbook/testing/test-data/components/index.q{xml}

每个测试都从一个由 `migrations/` 构建的空数据库开始。`test:given` 放入测试需要的行——
经过数据表结构的规则，所以应用本来不可能写入的行（`done` 不在 `CHECK (… IN …)` 之内、
缺少无法填写的必填列）会让这一步失败，而不是悄悄混进去。`test:as` 像登录那样让一个用户登录：

<<< @/../examples/cookbook/testing/test-data/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/testing/test-data/output/test-report.txt{text}

`no-text` 检查页面上*不能*出现的内容——这里是另一个用户的任务和一个已完成的任务。
完整的词汇见 [Testing an App](../../../guide/testing.md) 指南（英文）。

*已测试：* 本页导入了 `examples/cookbook/testing/test-data/` 中的文件，
上面的结果就是运行它们得到的报告。
