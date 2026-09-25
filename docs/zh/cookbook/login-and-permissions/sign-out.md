---
order: 5
title: "退出登录"
description: "一个清空会话并重定向的退出页面；受保护的页面重新关闭。"
source: cookbook/login-and-permissions/sign-out.md
source_hash: 86548aa4610b
---

# 退出登录

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/cookbook/login-and-permissions/sign-out)为准。
:::

**任务：** 结束用户的会话。

<<< @/../examples/cookbook/login-and-permissions/sign-out/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/index.q{xml}

页面可以修改会话然后重定向：它在 `q:redirect` 之前写入会话的内容会保留下来。

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/logout.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/components/login.q{xml}

测试先登录，再退出，然后检查首页再次要求登录：

<<< @/../examples/cookbook/login-and-permissions/sign-out/tests/logout.test.q{xml}

<<< @/../examples/cookbook/login-and-permissions/sign-out/output/test-report.txt{text}
