# zh-CN glossary (简体中文术语表)

Terms used in the Simplified Chinese pages, so every page says the same thing
the same way. Not a site page: docs/.vitepress/ is not published.

## Never translated

Keep these exactly as written, in `code` where the English has it:

- Quantum, VitePress, Python, SQLite, PostgreSQL, MySQL, Ollama, PyPI, GitHub,
  pip, npm, JavaScript, HTML, XML, RAG, LLM, SPA, React Native, Godot
- Every tag and namespace: `q:component`, `q:set`, `q:query`, `q:action`,
  `q:llm`, `q:knowledge`, `q:agent`, `ui:*`, `test:expect`… and the prefixes
  `q:`, `ui:`, `qg:`, `qt:`
- Every attribute (`name`, `datasource`, `required`, `minlength`, `flash`…)
- Commands and flags: `quantum run`, `quantum start`, `quantum stop`,
  `quantum test`, `quantum check`, `quantum console`, `quantum desktop`,
  `--port`, `pip install`
- File and folder names: `quantum.config.yaml`, `components/`, `migrations/`,
  `*.test.q`, `.q`, `SPEC.md`, `SUPPORT_TIERS.md`
- Rule IDs: `LOOP-2`, `DB-4`, `IA-6`…
- The tier names are translated (below), but when a sentence quotes the policy
  word itself, add the English in parentheses the first time: 核心层（Core）.

## Terms

| English | 简体中文 | Note |
|---|---|---|
| component | 组件 | |
| page | 页面 | |
| action | 动作 | a `q:action`; "表单动作" when it handles a form |
| form | 表单 | |
| field | 字段 | |
| query | 查询 | |
| datasource | 数据源 | |
| migration | 迁移 | |
| database | 数据库 | |
| table (database) | 数据表 / 表 | |
| row | 行 | |
| flash message | 提示消息（flash） | |
| redirect | 重定向 | |
| session | 会话 | |
| scope | 作用域 | |
| expression | 表达式 | |
| databinding | 数据绑定 | |
| tag | 标签 | |
| attribute | 属性 | |
| parser | 解析器 | |
| runtime | 运行时 | |
| build chain | 构建工具链 | |
| front-end framework | 前端框架 | |
| knowledge base | 知识库 | |
| agent | 智能体（agent） | |
| tool (of an agent) | 工具 | |
| model / language model | 模型 / 语言模型 | |
| embedding | 嵌入 | |
| chunk | 文本块 | |
| cite its sources | 引用来源 | |
| failure contract | 失败约定 | |
| tier | 层级 | |
| Core | 核心层 | |
| AI (tier) | AI 层 | |
| Experimental | 实验层 | |
| Laboratory | 实验室 | |
| stable | 稳定 | |
| semantic versioning | 语义化版本（semver） | |
| specification (SPEC) | 规范（SPEC） | |
| rule (of the SPEC) | 规则 | |
| conformance test | 一致性测试 | |
| test suite | 测试套件 | |
| recipe (Cookbook) | 示例 | the Cookbook is 实用示例 |
| release | 版本发布 / 发布 | |
| changelog | 更新日志 | |
| sponsor | 赞助 | |
| issue (GitHub) | Issue | kept in English, as Chinese developers write it |
| pull request | Pull Request | |
| virtual environment | 虚拟环境 | |
| extra (pip) | 可选依赖（extra） | |
| terminal / console | 终端 | |
| desktop window | 桌面窗口 | |

## Tone

Plain and direct, as the English: short sentences, no marketing words (不用
"强大"、"革命性"、"极致"). Use full-width punctuation in Chinese text (，。：；（）),
and half-width inside `code`. Put a space between Chinese and Latin words or
numbers (使用 Quantum 编写, 5 分钟).

## Machine-translated pages

Until a native speaker reviews a page, it starts with this notice (and links
to its English original):

```md
::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/path/to/english)为准。
:::
```
