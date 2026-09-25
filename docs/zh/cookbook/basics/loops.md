---
order: 3
title: "循环"
description: "用 q:loop 遍历列表（带位置）、数字范围和逗号分隔的文本。"
source: cookbook/basics/loops.md
source_hash: d76dbb1437b0
---

# 循环

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/loops)为准。
:::

**任务：** 对列表中的每一项或范围中的每个数字，重复页面的一部分。

<<< @/../examples/cookbook/basics/loops/quantum.config.yaml{yaml}

`type="array"` 遍历一个列表，`index=` 给从 0 开始的位置命名。
`type="range"` 从 `from` 数到 `to`（两端都包含），步长为 `step`。
`type="list"` 按逗号拆分文本，并去掉每一项两端的空格。

<<< @/../examples/cookbook/basics/loops/components/index.q{xml}

<<< @/../examples/cookbook/basics/loops/tests/loops.test.q{xml}

<<< @/../examples/cookbook/basics/loops/output/test-report.txt{text}

要遍历查询结果的行，参见[一个页面上的多个表单](../forms-and-actions/several-actions.md)。
规则：[LOOP-5](../../../reference/spec.md#LOOP-5) 和 [LOOP-6](../../../reference/spec.md#LOOP-6)。
