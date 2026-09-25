---
order: 4
title: "一个页面上的多个表单"
description: "每个表单和按钮都会提交它的动作名；页面没有的动作名返回 400。"
source: cookbook/forms-and-actions/several-actions.md
source_hash: 50553f79a7ea
---

# 一个页面上的多个表单

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/several-actions)为准。
:::

**任务：** 在一个页面上添加、删除和清空，每一项都有自己的动作。

<<< @/../examples/cookbook/forms-and-actions/several-actions/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/migrations/V001_cart.sql{sql}

每个 `ui:form on-submit` 和每个 `ui:button on-click` 都会在名为 `action` 的字段中
发送它的动作名；页面只运行这个动作，不运行其他动作。`with="id={cart.id}"`
随按钮发送这一行的 id。

<<< @/../examples/cookbook/forms-and-actions/several-actions/components/index.q{xml}

在有多个动作的页面上，如果提交中缺少 `action`，或者它不对应任何一个动作，
就会返回 `400` 并列出页面上的动作。不会有其他动作代替它运行，最后一个测试检查了这一点：

<<< @/../examples/cookbook/forms-and-actions/several-actions/tests/cart.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/several-actions/output/test-report.txt{text}

参见 [ACT-5](../../../reference/spec.md#ACT-5)。
