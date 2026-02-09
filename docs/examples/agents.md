---
layout: doc
title: AI Agent Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/agents.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# AI Agent Examples

AI agents with `q:agent`, tools, and multi-agent teams.

<div class="related-links">
  <a href="/guide/agents" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-agent" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Agent Patterns

### Basic Agent

```xml
<q:agent name="assistant" model="gpt-4" max_iterations="5">
  <q:instruction>
    You are a helpful assistant. Answer questions concisely.
  </q:instruction>

  <q:execute task="{userQuestion}" />
</q:agent>

<p>Response: {assistant}</p>
```

### Agent with Tools

```xml
<q:agent name="calculator" model="phi3" max_iterations="5">
  <q:instruction>
    You are a calculator. Use the provided tools.
  </q:instruction>

  <q:tool name="add" description="Add two numbers">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:function name="doAdd">
      <q:return value="{a + b}" />
    </q:function>
  </q:tool>

  <q:tool name="multiply" description="Multiply two numbers">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:function name="doMultiply">
      <q:return value="{a * b}" />
    </q:function>
  </q:tool>

  <q:execute task="What is 5 + 3 * 2?" />
</q:agent>
```

### Multi-Agent Team

```xml
<q:team name="support">
  <q:agent name="classifier" model="gpt-3.5-turbo">
    <q:instruction>Classify the customer request type.</q:instruction>
  </q:agent>

  <q:agent name="responder" model="gpt-4">
    <q:instruction>Generate a helpful response based on classification.</q:instruction>
  </q:agent>

  <q:workflow>
    <q:step agent="classifier" output="category" />
    <q:step agent="responder" input="{category}" output="response" />
  </q:workflow>
</q:team>
```

### RAG (Retrieval Augmented Generation)

```xml
<q:agent name="researcher" model="gpt-4">
  <q:instruction>
    Answer questions using the provided context.
  </q:instruction>

  <q:tool name="search" description="Search knowledge base">
    <q:param name="query" type="string" required="true" />
    <q:function name="doSearch">
      <q:query name="docs" datasource="vectors">
        SELECT content FROM documents
        WHERE embedding <-> :queryEmbedding < 0.5
        LIMIT 5
      </q:query>
      <q:return value="{docs}" />
    </q:function>
  </q:tool>

  <q:execute task="{userQuery}" />
</q:agent>
```

## Related Categories

- [Functions](/examples/functions) - Define agent tools
- [Database Queries](/examples/queries) - Agent data access
- [Advanced](/examples/advanced) - Complex agent applications
