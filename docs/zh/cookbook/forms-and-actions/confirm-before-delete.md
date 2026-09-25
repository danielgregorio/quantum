---
order: 7
title: "删除前先确认"
description: "一个先提问的页面，通过链接进入，删除则由它的按钮以 POST 发出；不需要 JavaScript。"
source: cookbook/forms-and-actions/confirm-before-delete.md
source_hash: 8e2ffc39c3d9
---

# 删除前先确认

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/confirm-before-delete)为准。
:::

**任务：** 在删除前询问"确定吗？"，不用 JavaScript。

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/migrations/V001_contacts.sql{sql}

列表中是一个链接，而不是按钮。打开链接只会读取，所以它只能提问：

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/index.q{xml}

提问本身是一个单独的页面 `components/delete/[id].q`。它的按钮提交到 `remove` 动作，
该动作删除后返回列表。如果联系人已经不存在了（第二个标签页、刷新），页面会说明这一点，
而不是提问。

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/components/delete/[id].q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/tests/delete.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/confirm-before-delete/output/test-report.txt{text}
