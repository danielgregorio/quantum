---
order: 7
title: "用迁移添加一列"
description: "用一个新的迁移文件修改数据表结构；旧的迁移保持原样。"
source: cookbook/data-and-sql/add-a-column.md
source_hash: b48dec1e9084
---

# 用迁移添加一列

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/add-a-column)为准。
:::

**任务：** 商品需要一个库存数量，而数据库已经存在了。

<<< @/../examples/cookbook/data-and-sql/add-a-column/quantum.config.yaml{yaml}

第一个迁移创建了数据表：

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V001_products.sql{sql}

修改是第二个文件。迁移按顺序运行，每个只运行一次，每个都在自己的事务中；
已经应用的迁移永远不要编辑：

<<< @/../examples/cookbook/data-and-sql/add-a-column/migrations/V002_add_stock.sql{sql}

```bash
quantum migrate up
```

<<< @/../examples/cookbook/data-and-sql/add-a-column/components/index.q{xml}

每个测试都从由迁移构建的数据库开始，所以测试看到的是全新安装得到的数据表结构：

<<< @/../examples/cookbook/data-and-sql/add-a-column/tests/stock.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/add-a-column/output/test-report.txt{text}

更想写出你想要的数据表结构，让 Quantum 来写迁移？参见
[Project Structure](../../../guide/project-structure.md)（英文）中的 `quantum migrate plan`。
参见 [DB-6](../../../reference/spec.md#DB-6) 和 [DB-8](../../../reference/spec.md#DB-8)。
