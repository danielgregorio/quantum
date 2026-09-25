---
order: 1
title: "用哈希密码登录"
description: "用 verifyPassword 将密码与它的 bcrypt 哈希比对，开启会话，并让一个页面只对已登录用户开放。"
source: cookbook/login-and-permissions/login-with-hashed-password.md
source_hash: 76e6db18e085
---

# 用哈希密码登录

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/login-and-permissions/login-with-hashed-password)为准。
:::

**任务：** 让用户用电子邮件和密码登录，数据库只保存密码的哈希，并且某个页面只对已登录用户显示。

数据表保存的是 bcrypt 哈希（用 `hashPassword` 生成，见[注册示例](./sign-up.md)），
从不保存密码本身：

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/migrations/V001_users.sql{sql}

登录动作查找用户，并用 `verifyPassword` 检查密码。对于错误的密码、不存在的用户或空字段，
它返回 false，从不报错。成功时，它设置 `require_auth` 和 `require_role` 读取的会话变量。
`session.sessionExpiry` 是必需的：没有它的会话算作已过期。

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/login.q{xml}

首页用 `require_auth="true"` 要求一个已登录的会话：

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/components/index.q{xml}

错误的地址和错误的密码得到同样的消息，所以表单不会告诉陌生人哪些地址有账号：

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/tests/login.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/login-with-hashed-password/output/test-report.txt{text}

更多内容见 [Authentication](../../../guide/authentication.md) 指南（英文）。
