---
order: 4
title: "会重定向的守卫"
description: "带 q:redirect 的顶层 q:if 保护一个页面及其所有动作：没有会话的提交不会写入任何东西。"
source: cookbook/login-and-permissions/guard-that-redirects.md
source_hash: 94e99b99ab2d
---

# 会重定向的守卫

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/login-and-permissions/guard-that-redirects)为准。
:::

**任务：** 把未登录的访问者带着一条消息送到登录页面，并确保他们也无法向页面的动作提交数据。

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/migrations/V001_notes.sql{sql}

位于页面顶部、分支中带有 `q:redirect` 的 `q:if` 就是一个**守卫**。它在页面之前、
也在页面的每个动作之前运行，所以直接发送到 `add` 的提交也会被拦下：

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/index.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/components/login.q{xml}

第二个测试在没有会话的情况下向动作提交，并检查没有写入任何行：

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/tests/guard.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/guard-that-redirects/output/test-report.txt{text}

守卫可以检查会话中的任何内容。如果只是要求已登录的用户或某个角色，`require_auth` 和
`require_role` 用一个属性就能表达（[只对一个角色开放的页面](./page-for-one-role.md)）。
