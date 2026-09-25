---
order: 2
title: "注册并保存密码哈希"
description: "用 hashPassword 创建账号，数据库从不保存密码本身，每个字段都有规则。"
source: cookbook/login-and-permissions/sign-up.md
source_hash: f0ed6cc4abc2
---

# 注册并保存密码哈希

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/login-and-permissions/sign-up)为准。
:::

**任务：** 创建账号，而且从不保存密码本身。

<<< @/../examples/cookbook/login-and-permissions/sign-up/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/migrations/V001_users.sql{sql}

`hashPassword(password)` 每次都用新的盐返回一个 bcrypt 哈希；`INSERT` 保存的就是它。
`q:param` 的规则最先运行：少于 12 个字符的密码永远不会到达查询。

<<< @/../examples/cookbook/login-and-permissions/sign-up/components/index.q{xml}

测试查看数据表：这一行保存的是 bcrypt 哈希（以 `$2b$` 开头），而且没有任何一行保存了原样输入的密码：

<<< @/../examples/cookbook/login-and-permissions/sign-up/tests/signup.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-up/output/test-report.txt{text}

要用这个哈希登录，参见[用哈希密码登录](./login-with-hashed-password.md)。
