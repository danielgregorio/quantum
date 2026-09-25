---
order: 1
title: "在每个字段旁显示它的错误"
description: "把规则在动作的 q:param 上写一次；表单读取它们，并在每个字段旁显示被拒绝的原因。"
source: cookbook/forms-and-actions/field-errors.md
source_hash: 25cb71a331e3
---

# 在每个字段旁显示它的错误

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/field-errors)为准。
:::

**任务：** 拒绝一个错误的表单，并在每个字段旁说明它哪里不对。

<<< @/../examples/cookbook/forms-and-actions/field-errors/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/migrations/V001_guests.sql{sql}

规则只写一次，写在动作的 `q:param` 上。`ui:form` 读取它们并放到自己的字段上
（`required`、`minlength`、`type="number"`、`min`……），所以浏览器先检查。
服务器会再检查一次，所有字段一起检查：只要有一个失败，动作就不会运行，页面返回，
每个字段显示自己的消息。

<<< @/../examples/cookbook/forms-and-actions/field-errors/components/index.q{xml}

在测试中，`error="field"` 检查该字段被拒绝，`message=` 检查它旁边显示的文本：

<<< @/../examples/cookbook/forms-and-actions/field-errors/tests/guests.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/field-errors/output/test-report.txt{text}

规则及其消息：[ACT-2](../../../reference/spec.md#ACT-2) 和
[UI-9](../../../reference/spec.md#UI-9)。
