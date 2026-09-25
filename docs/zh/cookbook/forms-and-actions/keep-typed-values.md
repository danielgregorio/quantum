---
order: 2
title: "被拒绝的表单保留已输入的内容"
description: "被拒绝后，表单会带着提交的值返回一次，这样没有人需要把一条长消息输入两遍。"
source: cookbook/forms-and-actions/keep-typed-values.md
source_hash: fb01e4e771dc
---

# 被拒绝的表单保留已输入的内容

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/keep-typed-values)为准。
:::

**任务：** 当服务器拒绝一个表单时，把它连同用户输入的内容一起返回，而不是空的。

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/migrations/V001_messages.sql{sql}

这不需要写任何东西。被拒绝之后，`ui:form` 的下一次渲染会用提交的值填充每个字段，
只填一次，就像提示消息（flash）一样。密码字段和文件字段永远不会被带回。
`rows="6"` 让消息成为一个多行字段。

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/components/index.q{xml}

第一个测试提交一个错误的地址和一条正确的消息：地址被拒绝，消息仍然留在它的字段里。
第二个测试再次打开页面：值已经不在了。

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/tests/contact.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/output/test-report.txt{text}

参见 [UI-9](../../../reference/spec.md#UI-9)，多行字段见
[UI-14](../../../reference/spec.md#UI-14)。
