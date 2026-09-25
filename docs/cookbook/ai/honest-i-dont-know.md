---
order: 2
title: When the documents do not know
description: "minRelevance keeps unrelated chunks out; with nothing left, the model is not asked and the page says so."
---

# When the documents do not know

**Task:** when the documents do not cover a question, say so — instead of
letting the model answer from memory.

<<< @/../examples/cookbook/ai/honest-i-dont-know/quantum.config.yaml{yaml}

The same three documents as in [Answers with their sources](./answer-with-sources.md).
Without `minRelevance`, the nearest chunks always come back, related to the
question or not. With it, a chunk less relevant than the floor is dropped;
when none is left, `answer_result.found` is false and the model is never
called.

<<< @/../examples/cookbook/ai/honest-i-dont-know/components/index.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/tests/honest.test.q{xml}

<<< @/../examples/cookbook/ai/honest-i-dont-know/output/test-report.txt{text}

The floor depends on the embedding model and the chunk size. Print
`s.relevance` for a few questions your documents answer, and a few they do
not, and put the floor between them — the page above shows it next to each
source for that reason.

*Tested:* in CI these tests run against a stand-in model server, which answers from the first source it is given; before every release they run against a real model (`tests/live_ai/test_cookbook_ai.py`). That is why they check structure — which source, which tool, what the page shows on failure — and never the model's words.

See [IA-9](../../reference/spec.md#IA-9).
