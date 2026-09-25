---
order: 5
title: When the model fails
description: "onerror on q:llm: a model that is down or too slow does not take the page down with it."
---

# When the model fails

**Task:** a page that uses a model should still work — and say what
happened — when the model server is down, slow, or missing the model.

<<< @/../examples/cookbook/ai/when-the-model-fails/quantum.config.yaml{yaml}

Without `onerror`, an AI failure stops the page with an error that names the
server and the cause. With `onerror="continue"`, the page goes on:
`summary_result.success` is false, `summary_result.error.message` says why,
and `summary` is empty. The example points `endpoint=` at a server that is not
running, so it fails the same way everywhere.

<<< @/../examples/cookbook/ai/when-the-model-fails/components/index.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/tests/failure.test.q{xml}

<<< @/../examples/cookbook/ai/when-the-model-fails/output/test-report.txt{text}

`onerror` works the same on `q:llm`, `q:knowledge`, `q:agent` and `q:query`.

See [IA-5](../../reference/spec.md#IA-5).
