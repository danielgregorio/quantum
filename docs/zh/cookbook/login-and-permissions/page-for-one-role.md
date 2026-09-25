---
order: 3
title: "只对一个角色开放的页面"
description: "require_role 让页面只对管理员开放：普通成员得到 403，未登录的访问者被带去登录。"
source: cookbook/login-and-permissions/page-for-one-role.md
source_hash: 8674b9cce0ea
---

# 只对一个角色开放的页面

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/login-and-permissions/page-for-one-role)为准。
:::

**任务：** 只向管理员显示一个页面。

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/quantum.config.yaml{yaml}

`require_auth="true"` 要求一个已登录的会话；`require_role` 要求 `session.userRole`
是列出的角色之一（多个角色用逗号分隔，`require_role="admin,editor"`）：

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/reports.q{xml}

没有会话时，响应会重定向到 `/login`（用 `security.login_url` 修改）：

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/components/login.q{xml}

`test:as` 让测试的会话以某个角色登录，不需要密码：

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/tests/reports.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/page-for-one-role/output/test-report.txt{text}
