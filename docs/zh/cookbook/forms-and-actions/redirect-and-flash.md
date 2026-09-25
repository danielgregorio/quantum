---
order: 3
title: "重定向并说明发生了什么"
description: "用 q:redirect 和提示消息结束动作；警告用 q:flash；消息在下一个页面上显示一次。"
source: cookbook/forms-and-actions/redirect-and-flash.md
source_hash: 1783ffa2ce2e
---

# 重定向并说明发生了什么

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/redirect-and-flash)为准。
:::

**任务：** 表单提交之后，把浏览器带到一个页面，并告诉它发生了什么，只说一次。

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/migrations/V001_notes.sql{sql}

`q:redirect` 结束动作。它的 `flash` 接受表达式，并成为下一个渲染的页面上的 `flash`，
同时 `flashType` 设为 `success`。如果要另一种消息，`q:flash type="warning"` 在重定向
之前设置这两者。URL 可以是应用中的任何页面。

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/done.q{xml}

第二个测试在重定向后再次打开页面：提示消息已经消失，`flash` 为 `''`。

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/tests/notes.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/output/test-report.txt{text}

参见 [ACT-3](../../../reference/spec.md#ACT-3)。
