---
order: 5
title: "各种字段"
description: "用 ui:formitem 加标签的 ui:form：文本、数字、带选项的下拉框、开关、单选按钮和多行字段。"
source: cookbook/screens/form-fields.md
source_hash: ef4d1aa946f9
---

# 各种字段

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/screens/form-fields)为准。
:::

**任务：** 一个使用每种字段、并带标签的表单。

<<< @/../examples/cookbook/screens/form-fields/quantum.config.yaml{yaml}

`ui:formitem label="…"` 在字段旁边放一个标签。`ui:select` 从带有各自文本的
`ui:option` 中获取选项，`ui:radio` 则从动作的 `q:param` 的 `enum` 中获取。
`ui:switch` 是一个布尔值的开关，`rows` 生成多行字段。每个字段的规则都来自动作
（[在每个字段旁显示它的错误](../forms-and-actions/field-errors.md)）。

<<< @/../examples/cookbook/screens/form-fields/components/index.q{xml}

<<< @/../examples/cookbook/screens/form-fields/tests/booking.test.q{xml}

<<< @/../examples/cookbook/screens/form-fields/output/test-report.txt{text}

参见 [UI-9](../../../reference/spec.md#UI-9) 和 [UI-14](../../../reference/spec.md#UI-14)。
