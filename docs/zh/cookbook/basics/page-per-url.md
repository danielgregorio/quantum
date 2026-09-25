---
order: 6
title: "每个 URL 一个页面"
description: "components/product/[id].q 响应 /product/1、/product/2……；这个路径段是一个变量。"
source: cookbook/basics/page-per-url.md
source_hash: b03561c27215
---

# 每个 URL 一个页面

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/page-per-url)为准。
:::

**任务：** 用一个文件为每一项响应一个 URL。

<<< @/../examples/cookbook/basics/page-per-url/quantum.config.yaml{yaml}

文件名或文件夹名中的 `[name]` 路径段可以匹配任何值，页面会把它作为变量 `name`
得到。它以文本形式到达；在 `q:set` 上加 `type="integer"` 可以把它变成数字。

<<< @/../examples/cookbook/basics/page-per-url/components/product/[id].q{xml}

<<< @/../examples/cookbook/basics/page-per-url/tests/product.test.q{xml}

<<< @/../examples/cookbook/basics/page-per-url/output/test-report.txt{text}

有数据库时，页面按这个 id 读取对应的行：参见
[编辑一行](../forms-and-actions/edit-a-row.md)。规则：
[ROUTE-1](../../../reference/spec.md#ROUTE-1)。
