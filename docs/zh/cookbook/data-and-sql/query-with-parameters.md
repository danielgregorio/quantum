---
order: 1
title: "带参数的查询"
description: "按 URL 中的值筛选，并绑定为 q:param——这个值永远不会变成 SQL。"
source: cookbook/data-and-sql/query-with-parameters.md
source_hash: b54ace8bb289
---

# 带参数的查询

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/query-with-parameters)为准。
:::

**任务：** 安全地列出名字中包含 URL 所要求内容（`/?name=mouse`）的商品。

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/migrations/V001_products.sql{sql}

SQL 中的每个 `:name` 都绑定到同名的 `q:param`：值与 SQL 文本分开发送到数据库，
并先按它的 `type` 转换。没有 `q:param` 的 `:name` 无法通过解析，所以不可能意外地把
一个值粘贴进 SQL。

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/components/index.q{xml}

最后一个测试在 URL 中发送 SQL。它只是一段要搜索的文本：没有哪个商品的名字包含它，
数据表也完好无损。

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/tests/products.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/query-with-parameters/output/test-report.txt{text}

参见 [DB-1](../../../reference/spec.md#DB-1)。
