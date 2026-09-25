---
order: 6
title: Sort messages with JSON answers
description: "responseFormat json: the model's answer is an object whose fields you check and store."
---

# Sort messages with JSON answers

**Task:** file each support message under a category, decided by the model,
in a table.

<<< @/../examples/cookbook/ai/sort-tickets-with-json/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/migrations/V001_tickets.sql{sql}

`responseFormat="json"` asks the model for JSON and parses it: `ticket` is an
object. Its fields are input like any other — the page checks the category
before storing it, and the action's own `q:param` rules run before the model
is ever called.

<<< @/../examples/cookbook/ai/sort-tickets-with-json/components/index.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/tickets.test.q{xml}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/sort-tickets-with-json/output/test-report.txt{text}

*Tested:* in CI these tests run against a stand-in model server, which answers from the first source it is given; before every release they run against a real model (`tests/live_ai/test_cookbook_ai.py`). That is why they check structure — which source, which tool, what the page shows on failure — and never the model's words.

See [IA-1](../../reference/spec.md#IA-1).
