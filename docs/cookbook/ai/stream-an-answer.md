---
order: 3
title: Stream an answer
description: "A streamed q:llm and ui:stream: the page renders at once, the answer appears as it is written."
---

# Stream an answer

**Task:** a model can take seconds to answer; show the page at once and the
answer as it arrives.

<<< @/../examples/cookbook/ai/stream-an-answer/quantum.config.yaml{yaml}

With `stream="true"`, `q:llm` does not wait: the retrieval is done, so the
sources are on the page, and `<ui:stream for="answer">` fills in the answer as
the model writes it — through the framework's own script, with no JavaScript
to write. Without JavaScript it is a link, and `quantum console` shows the
answer arriving too.

<<< @/../examples/cookbook/ai/stream-an-answer/components/index.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/tests/stream.test.q{xml}

<<< @/../examples/cookbook/ai/stream-an-answer/output/test-report.txt{text}

The stream belongs to the visitor who asked, is read once and expires in ten
minutes.

*Tested:* in CI these tests run against a stand-in model server, which answers from the first source it is given; before every release they run against a real model (`tests/live_ai/test_cookbook_ai.py`). That is why they check structure — which source, which tool, what the page shows on failure — and never the model's words.

See [IA-7](../../reference/spec.md#IA-7).
