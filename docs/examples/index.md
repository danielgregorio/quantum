---
layout: doc
title: Examples Gallery
---

<script setup>
import { ref, onMounted } from 'vue'

const categories = ref([])
const totalExamples = ref(0)

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/index.json')
    categories.value = data.categories || []
    totalExamples.value = data.totalExamples || 0
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Examples Gallery

Explore **150+ working examples** organized by feature. Each example is a complete, runnable `.q` file demonstrating Quantum Framework capabilities.

<div class="gallery-stats">
  <div class="stat-item">
    <span class="stat-value">{{ totalExamples }}</span>
    <span class="stat-label">Examples</span>
  </div>
  <div class="stat-item">
    <span class="stat-value">{{ categories.length }}</span>
    <span class="stat-label">Categories</span>
  </div>
  <div class="stat-item">
    <span class="stat-value">3</span>
    <span class="stat-label">Difficulty Levels</span>
  </div>
</div>

## Browse by Category

<div class="category-grid">
  <CategoryCard
    v-for="cat in categories"
    :key="cat.id"
    v-bind="cat"
  />
</div>

## Quick Reference

| Category | Description | Examples |
|----------|-------------|----------|
| [State Management](/examples/state-management) | Variables with `q:set`, data binding | 30 |
| [Loops](/examples/loops) | Iteration with `q:loop` | 7 |
| [Conditionals](/examples/conditionals) | Logic with `q:if`/`q:else` | 9 |
| [Functions](/examples/functions) | Reusable code with `q:function` | 16 |
| [Database Queries](/examples/queries) | SQL with `q:query` | 16 |
| [Forms & Actions](/examples/forms-actions) | User input handling | 8 |
| [Authentication](/examples/authentication) | Login, roles, protected routes | 4 |
| [AI Agents](/examples/agents) | LLM integration with `q:agent` | 6 |
| [UI & Theming](/examples/ui-theming) | Components, themes, animations | 10 |
| [Games](/examples/games) | 2D games with `qg:scene` | 9 |
| [Data Import](/examples/data-import) | CSV, JSON, XML loading | 7 |
| [Advanced](/examples/advanced) | Multi-feature applications | 28 |

## Running Examples

### Command Line

```bash
# Run any example
python src/cli/runner.py run examples/hello.q

# With debug output
python src/cli/runner.py run examples/test-set-simple.q --debug

# Start web server for web apps
python src/cli/runner.py start
```

### From Source

All examples are available in the [examples/](https://github.com/danielgregorio/quantum/tree/main/examples) directory on GitHub.

## Difficulty Levels

- <span class="badge badge-beginner">Beginner</span> - Simple examples with 1-2 features, under 50 lines
- <span class="badge badge-intermediate">Intermediate</span> - Moderate complexity, 3-5 features, 50-150 lines
- <span class="badge badge-advanced">Advanced</span> - Complex applications with multiple features, 150+ lines

## Next Steps

- New to Quantum? Start with [State Management examples](/examples/state-management)
- Building web apps? Check [Forms & Actions](/examples/forms-actions)
- Interested in AI? Explore [AI Agents](/examples/agents)
- Want to see it all? Browse [Advanced examples](/examples/advanced)
