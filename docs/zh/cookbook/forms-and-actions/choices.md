---
order: 9
title: "从列表中选择"
description: "q:param 上的 enum 为 ui:select 和 ui:radio 提供选项，并拒绝其他任何值；复选框是一个布尔值。"
source: cookbook/forms-and-actions/choices.md
source_hash: 52d2092cd49d
---

# 从列表中选择

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/choices)为准。
:::

**任务：** 一个从列表中取一个值的字段，以及一个是/否复选框。

<<< @/../examples/cookbook/forms-and-actions/choices/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/choices/migrations/V001_orders.sql{sql}

列表只写一次，作为动作的 `q:param` 上的 `enum`。没有自己选项的 `ui:select` 或
`ui:radio` 会从这里获取选项，服务器会拒绝不在列表中的值。`default` 补上省略的字段。
复选框只有勾选时才会发送值，所以 `type="boolean"` `default="false"` 让它成为
`true` 或 `false`。

<<< @/../examples/cookbook/forms-and-actions/choices/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/tests/order.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/choices/output/test-report.txt{text}

参见 [ACT-2](../../../reference/spec.md#ACT-2) 和 [UI-9](../../../reference/spec.md#UI-9)。
