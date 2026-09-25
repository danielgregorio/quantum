---
order: 8
title: "数字和日期"
description: "q:param 上的 type=integer、decimal 和 date：动作得到经过检查的数字和真实的日期，带 min 和 max。"
source: cookbook/forms-and-actions/numbers-and-dates.md
source_hash: be7e0a2f2ba4
---

# 数字和日期

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/numbers-and-dates)为准。
:::

**任务：** 接收一个金额、一个数量和一个日期，并用它们计算，而不必手动转换任何东西。

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/migrations/V001_expenses.sql{sql}

表单发送的是文本。`type="decimal"` 和 `type="integer"` 在动作运行之前把它变成数字，
所以 `amount / people` 可以计算。`min` 和 `max` 针对这个数字检查。`type="date"`
接受 `YYYY-MM-DD` 格式且真实存在的日期，并把它保留为文本，可以直接存入数据库。

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/components/index.q{xml}

表单得到带同样 `min` 和 `max` 的 `type="number"` 以及 `type="date"`，所以浏览器先检查。
测试像脚本一样直接向服务器提交：

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/tests/split.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/numbers-and-dates/output/test-report.txt{text}

参见 [ACT-2](../../../reference/spec.md#ACT-2) 和 [UI-9](../../../reference/spec.md#UI-9)。
