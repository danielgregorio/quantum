---
order: 1
title: "开发中的邮件"
description: "开发时不需要邮件服务器也能从动作发送邮件——host: log 把每封邮件写入日志。"
source: cookbook/files-and-mail/mail-in-development.md
source_hash: 6103acae1466
---

# 开发中的邮件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/files-and-mail/mail-in-development)为准。
:::

**任务：** 一个给支持团队发邮件的联系表单——而且你可以在没有邮件服务器的情况下开发和测试它。

使用 `host: log` 时，`q:mail` 把每封邮件写入日志，而不是发送出去。配置从环境变量读取
主机，所以生产环境只需设置 `SMTP_HOST`：

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

测试提交表单，检查访问者得到的提示，以及错误的地址在发送任何内容之前就在它的字段上被拒绝：

<<< @/../examples/cookbook/files-and-mail/mail-in-development/tests/contact.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/test-report.txt{text}

这是第一个测试"发送"的邮件——也就是 `host: log` 写下的内容：

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/mail.txt{text}

没有 `mail:` 部分时，`q:mail` 会报错并说明原因——它从不假装已经发送。更多内容见
[Files & Mail](../../../guide/files-and-mail.md)（英文）。

*已测试：* 本页导入了 `examples/cookbook/files-and-mail/mail-in-development/` 中的文件，
上面的结果来自运行它们。
