---
order: 1
title: Answers with their sources
description: "Answer questions from your own documents with q:knowledge and q:llm knowledge=, and list the sources."
---

# Answers with their sources

**Task:** a page that answers questions about a store from its policy
documents, and shows which document each answer came from.

<<< @/../examples/cookbook/ai/answer-with-sources/quantum.config.yaml{yaml}

Three Markdown files in `knowledge/`:

<<< @/../examples/cookbook/ai/answer-with-sources/knowledge/returns.md{md}

`q:knowledge` reads the folder, splits it into chunks and embeds them.
`q:llm knowledge="docs"` retrieves the chunks closest to the question and
sends them to the model numbered, with the instruction to answer only from
them and cite them like `[1]`. `answer_result.sources` lists what was
retrieved; `answer_result.grounded` says whether the answer cites any of it.

<<< @/../examples/cookbook/ai/answer-with-sources/components/index.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/tests/ask.test.q{xml}

<<< @/../examples/cookbook/ai/answer-with-sources/output/test-report.txt{text}

*Tested:* in CI these tests run against a stand-in model server, which answers from the first source it is given; before every release they run against a real model (`tests/live_ai/test_cookbook_ai.py`). That is why they check structure — which source, which tool, what the page shows on failure — and never the model's words.

See [IA-2](../../reference/spec.md#IA-2), [IA-6](../../reference/spec.md#IA-6)
and [the AI guide](../../guide/ai.md#answers-that-cite-their-sources).
