---
order: 3
title: "测试动作拒绝的内容"
description: "测试字段错误、业务规则和动作的成功——error=、message=、flash= 以及数据表。"
source: cookbook/testing/action-errors.md
source_hash: 2e4ddc8a6560
---

# 测试动作拒绝的内容

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/testing/action-errors)为准。
:::

**任务：** 证明一个表单拒绝了它应该拒绝的内容——违反规则的字段、业务上不允许的值——
并且在拒绝时什么都没有写入。

一个注册表单，有两种拒绝：`q:param` 的规则（在动作运行之前检查），以及动作本身中的
一条业务规则（这个地址已经是会员了）：

<<< @/../examples/cookbook/testing/action-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/action-errors/migrations/V001_members.sql{sql}

<<< @/../examples/cookbook/testing/action-errors/components/index.q{xml}

`error="name"` 检查提交被拒绝的字段，`message=` 检查它旁边显示的文本。
由动作自己决定的拒绝是一次带提示消息的重定向，用 `flash=` 检查。
`table=` 配合 `count=` 证明什么都没有写入：

<<< @/../examples/cookbook/testing/action-errors/tests/signup.test.q{xml}

<<< @/../examples/cookbook/testing/action-errors/output/test-report.txt{text}

`q:param` 接受的规则（`required`、`minlength`、`type="email"`、`enum`……）见
[Actions & Forms](../../../guide/actions.md)（英文）。

*已测试：* 本页导入了 `examples/cookbook/testing/action-errors/` 中的文件，
上面的结果就是运行它们得到的报告。
