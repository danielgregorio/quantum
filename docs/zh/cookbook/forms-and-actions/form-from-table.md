---
order: 5
title: "根据数据表生成表单"
description: "q:action table= 从数据表结构获取参数；没有字段的 ui:form 为每一列画一个字段。"
source: cookbook/forms-and-actions/form-from-table.md
source_hash: 8dcaa96980a9
---

# 根据数据表生成表单

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/forms-and-actions/form-from-table)为准。
:::

**任务：** 为一张数据表做一个表单，而不必把每个字段和每条规则再写一遍。

<<< @/../examples/cookbook/forms-and-actions/form-from-table/quantum.config.yaml{yaml}

数据表结构已经说明了一本书需要什么：

<<< @/../examples/cookbook/forms-and-actions/form-from-table/migrations/V001_library.sql{sql}

`<q:action table="books" datasource="db">` 读取它，按数据表的顺序，为除主键外的
每一列生成一个 `q:param`：

| 列 | 变成 |
|---|---|
| `title VARCHAR(120) NOT NULL` | 必填，最多 120 个字符 |
| `author_id ... REFERENCES authors(id)` | 一个必须对应已有作者的整数 |
| `genre ... CHECK (genre IN (...))` | 三者之一 |
| `pages INTEGER`（可以为 NULL） | 一个整数；留空时以 `None` 到达动作 |
| `lent BOOLEAN` | 一个复选框 |

没有自己字段的 `ui:form` 为每个参数画一个字段，标签取自名字（`author_id` 变成
"Author"）。作者字段是一个作者名字的列表。查询的 `pages` 参数上的 `null="true"`
把留空的值保存为 `NULL`。

<<< @/../examples/cookbook/forms-and-actions/form-from-table/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/tests/books.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/form-from-table/output/test-report.txt{text}

写在动作里的 `q:param` 优先于数据表结构中的，`columns="a,b"` 只保留这些列。参见
[UI-10](../../../reference/spec.md#UI-10)。
