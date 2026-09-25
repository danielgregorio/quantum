---
order: 2
title: "当邮件服务器拒绝时"
description: "即使确认邮件发不出去，也要保留订单——onerror=continue，并告诉访问者。"
source: cookbook/files-and-mail/mail-server-refuses.md
source_hash: 9ffe0f1d6c0a
---

# 当邮件服务器拒绝时

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/files-and-mail/mail-server-refuses)为准。
:::

**任务：** 即使确认邮件无法发送，订单也必须保存——访问者应该得到说明，而不是一个错误页面。

默认情况下，服务器不接受的 `q:mail` 会带着服务器给出的原因停止动作。
`onerror="continue"` 让动作继续，并把结果放在 `<name>_result` 中：`success`，
失败时还有 `error.message`。

这个示例指向一个不存在的邮件服务器，所以每封邮件都会失败——就像真实服务器宕机时一样：

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/migrations/V001_orders.sql{sql}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

订单在邮件之前插入，提示消息说明结果如何。测试两者都检查——这一行存在，访问者也得到了告知：

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/tests/order.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/output/test-report.txt{text}

在开发中，[`host: log`](./mail-in-development.md) 可以完全避免这种失败；
`onerror="continue"` 是为真实服务器宕机的那一天准备的。更多内容见
[Files & Mail](../../../guide/files-and-mail.md)（英文）。

*已测试：* 本页导入了 `examples/cookbook/files-and-mail/mail-server-refuses/` 中的文件，
上面的结果来自运行它们。
