---
order: 6
title: "变更历史"
description: "history: true 记录谁修改了哪一行、如何修改；ui:history 在页面上显示它。"
source: cookbook/data-and-sql/change-history.md
source_hash: c1de2e8e5d97
---

# 变更历史

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/change-history)为准。
:::

**任务：** 知道谁在什么时候修改了维基的某个页面，以及改了什么。

数据源上的 `history: true` 就是全部配置：

<<< @/../examples/cookbook/data-and-sql/change-history/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/change-history/migrations/V001_pages.sql{sql}

动作的每一次写入都会在同一个事务中，记录到同一个数据库的 `quantum_history` 数据表里：
时间、会话的用户、动作、这一行，以及修改前后的这一行。`ui:history` 按从新到旧列出
一行的变更，每个被修改的列显示为 `old → new`。

<<< @/../examples/cookbook/data-and-sql/change-history/components/index.q{xml}

`test:as` 让测试登录；`history=` 检查记录了什么。被拒绝或回滚的写入不会留下历史：

<<< @/../examples/cookbook/data-and-sql/change-history/tests/history.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/change-history/output/test-report.txt{text}

参见 [DB-11](../../../reference/spec.md#DB-11)。
