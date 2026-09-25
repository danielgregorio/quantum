---
order: 7
title: Answers from a table
description: "A q:knowledge source that is a query: the rows of your FAQ table, retrieved like documents."
---

# Answers from a table

**Task:** answer account questions from an FAQ kept in the database.

<<< @/../examples/cookbook/ai/knowledge-from-a-table/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/migrations/V001_faq.sql{sql}

A `type="query"` source turns each row into a text to index. Everything in it
is shared by every user of the app — any question can retrieve any row — so
index only what everyone may read.

<<< @/../examples/cookbook/ai/knowledge-from-a-table/components/index.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/tests/faq.test.q{xml}

<<< @/../examples/cookbook/ai/knowledge-from-a-table/output/test-report.txt{text}

*Tested:* in CI these tests run against a stand-in model server, which answers from the first source it is given; before every release they run against a real model (`tests/live_ai/test_cookbook_ai.py`). That is why they check structure — which source, which tool, what the page shows on failure — and never the model's words.

See [IA-8](../../reference/spec.md#IA-8) and [IA-9](../../reference/spec.md#IA-9).
