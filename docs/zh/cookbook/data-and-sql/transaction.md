---
order: 5
title: "一起发生的写入"
description: "一个 q:transaction：扣款、入账和日志记录一起提交，否则一个都不提交。"
source: cookbook/data-and-sql/transaction.md
source_hash: 3bce037be24a
---

# 一起发生的写入

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/data-and-sql/transaction)为准。
:::

**任务：** 在两个账户之间转账，确保钱绝不会从一个账户扣除却没有存入另一个账户。

<<< @/../examples/cookbook/data-and-sql/transaction/quantum.config.yaml{yaml}

日志表拒绝超过 1000 的转账——最后一个测试利用这一点让第三次写入失败：

<<< @/../examples/cookbook/data-and-sql/transaction/migrations/V001_accounts.sql{sql}

页面检查它能解释的情况（余额不足），并用提示消息（flash）说明。三次写入放在
`q:transaction` 中：只要其中任何一次失败，之前的写入就会回滚，页面带着错误停止。

<<< @/../examples/cookbook/data-and-sql/transaction/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/tests/transfer.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/transaction/output/test-report.txt{text}

参见 [DB-4](../../../reference/spec.md#DB-4)。
