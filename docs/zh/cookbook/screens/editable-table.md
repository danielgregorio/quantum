---
order: 2
title: "可以就地编辑的表格"
description: "ui:table 的 edit= 把每个单元格变成一个按数据表结构检查的小表单；不需要编写动作。"
source: cookbook/screens/editable-table.md
source_hash: f6364e25b3ad
---

# 可以就地编辑的表格

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/screens/editable-table)为准。
:::

**任务：** 让用户不打开编辑页面就能修改表格中的一个值。

<<< @/../examples/cookbook/screens/editable-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/screens/editable-table/migrations/V001_items.sql{sql}

`edit="items"` 让每个单元格成为一个保存某一行某一列的小表单。数据表的结构就是规则：
因为 `CHECK`，`shelf` 必须是 A、B 或 C，被拒绝的值会以错误提示消息（flash）返回。
带 `edit="false"` 的列只显示、不编辑，强行提交的请求会得到 `400`。
`sort="true"` 在表头上加上排序链接。

<<< @/../examples/cookbook/screens/editable-table/components/index.q{xml}

测试像浏览器一样，用 `__edit` 动作编辑一个单元格：

<<< @/../examples/cookbook/screens/editable-table/tests/stock.test.q{xml}

<<< @/../examples/cookbook/screens/editable-table/output/test-report.txt{text}

参见 [UI-5](../../../reference/spec.md#UI-5) 和 [UI-13](../../../reference/spec.md#UI-13)。
