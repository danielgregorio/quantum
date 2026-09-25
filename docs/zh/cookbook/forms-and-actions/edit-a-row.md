---
order: 6
title: "编辑一行"
description: "用 [id].q 为每一行提供一个页面，表单打开时带着这一行的值，保存时应用数据表的规则。"
source: cookbook/forms-and-actions/edit-a-row.md
source_hash: 5e7078307baa
---

# 编辑一行

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/edit-a-row)为准。
:::

**任务：** 一个从列表进入、编辑一本书的页面。

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/migrations/V001_books.sql{sql}

列表把每本书链接到 `/book/{id}`：

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/index.q{xml}

`components/book/[id].q` 以 `id = 2` 响应 `/book/2`。动作从数据表中获取 `title` 和
`genre`（[根据数据表生成表单](./form-from-table.md)），`values="{book}"`
让表单打开时带着这一行的值。一个只返回一行的查询就够了。

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/components/book/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/tests/edit.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/edit-a-row/output/test-report.txt{text}

参见 [UI-10](../../../reference/spec.md#UI-10)。
