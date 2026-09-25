---
order: 4
title: An agent over your database
description: "q:agent with a read-only query tool: the model picks the tool and its arguments, never the SQL."
---

# An agent over your database

**Task:** let an assistant answer "which products are running out?" from the
shop's database, without ever letting the model write SQL.

<<< @/../examples/cookbook/ai/agent-over-your-database/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/ai/agent-over-your-database/migrations/V001_products.sql{sql}

The tool is a function you write, with one read-only query. The model sees
its name, its description and its parameter; it chooses to call it and with
which value, and that value is converted to the parameter's type before the
query runs. `stock_result.actions` lists every call, written out.

<<< @/../examples/cookbook/ai/agent-over-your-database/components/index.q{xml}

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/agent.test.q{xml}

In CI, the stand-in model follows a short script — call the tool, then
finish:

<<< @/../examples/cookbook/ai/agent-over-your-database/tests/fake-model.json{json}

<<< @/../examples/cookbook/ai/agent-over-your-database/output/test-report.txt{text}

A tool can do whatever its body does, and a prompt can steer the model into
calling it: give tools only the access the task needs.

*Tested:* in CI these tests run against a stand-in model server, which answers from the first source it is given; before every release they run against a real model (`tests/live_ai/test_cookbook_ai.py`). That is why they check structure — which source, which tool, what the page shows on failure — and never the model's words.

See [IA-4](../../reference/spec.md#IA-4) and [IA-5](../../reference/spec.md#IA-5).
