---
order: 7
title: "读取查询字符串"
description: "query.name 读取地址中的 ?name=；default 处理缺失的值；urlencode 生成链接。"
source: cookbook/basics/query-string.md
source_hash: 04f0affeada2
---

# 读取查询字符串

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/basics/query-string)为准。
:::

**任务：** 根据地址中的值筛选和排序一个列表。

<<< @/../examples/cookbook/basics/query-string/quantum.config.yaml{yaml}

`query.q` 是地址中 `?q=` 的值；地址中没有它时为空，所以用 `default` 给它一个值。
GET 表单会替你填好地址。`urlencode()` 让输入的值可以安全地放进链接里。

<<< @/../examples/cookbook/basics/query-string/components/index.q{xml}

<<< @/../examples/cookbook/basics/query-string/tests/search.test.q{xml}

<<< @/../examples/cookbook/basics/query-string/output/test-report.txt{text}

参见 [SET-1](../../../reference/spec.md#SET-1) 和 [EXPR-12](../../../reference/spec.md#EXPR-12)。
