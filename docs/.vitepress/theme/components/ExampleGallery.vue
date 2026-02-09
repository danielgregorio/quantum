<script setup>
import { ref, computed } from 'vue'
import ExampleCard from './ExampleCard.vue'

const props = defineProps({
  examples: { type: Array, required: true },
  showFilters: { type: Boolean, default: true }
})

const selectedComplexity = ref('')
const searchQuery = ref('')

const filteredExamples = computed(() => {
  let result = props.examples

  if (selectedComplexity.value) {
    result = result.filter(ex => ex.complexity === selectedComplexity.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(ex =>
      ex.title.toLowerCase().includes(query) ||
      ex.description.toLowerCase().includes(query) ||
      ex.file.toLowerCase().includes(query) ||
      ex.tags?.some(tag => tag.toLowerCase().includes(query)) ||
      ex.features?.some(f => f.toLowerCase().includes(query))
    )
  }

  return result
})

const complexityStats = computed(() => {
  const stats = { beginner: 0, intermediate: 0, advanced: 0 }
  props.examples.forEach(ex => {
    if (stats[ex.complexity] !== undefined) {
      stats[ex.complexity]++
    }
  })
  return stats
})
</script>

<template>
  <div class="example-gallery">
    <div class="filters" v-if="showFilters">
      <div class="filter-group">
        <label class="filter-label">Complexity</label>
        <div class="complexity-filters">
          <button
            class="complexity-btn"
            :class="{ active: selectedComplexity === '' }"
            @click="selectedComplexity = ''"
          >
            All ({{ examples.length }})
          </button>
          <button
            class="complexity-btn beginner"
            :class="{ active: selectedComplexity === 'beginner' }"
            @click="selectedComplexity = 'beginner'"
          >
            Beginner ({{ complexityStats.beginner }})
          </button>
          <button
            class="complexity-btn intermediate"
            :class="{ active: selectedComplexity === 'intermediate' }"
            @click="selectedComplexity = 'intermediate'"
          >
            Intermediate ({{ complexityStats.intermediate }})
          </button>
          <button
            class="complexity-btn advanced"
            :class="{ active: selectedComplexity === 'advanced' }"
            @click="selectedComplexity = 'advanced'"
          >
            Advanced ({{ complexityStats.advanced }})
          </button>
        </div>
      </div>

      <div class="filter-group search-group">
        <label class="filter-label">Search</label>
        <div class="search-wrapper">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by name, tag, or feature..."
            class="search-input"
          />
        </div>
      </div>
    </div>

    <div class="results-info" v-if="filteredExamples.length !== examples.length">
      Showing {{ filteredExamples.length }} of {{ examples.length }} examples
    </div>

    <div class="gallery-grid" v-if="filteredExamples.length">
      <ExampleCard
        v-for="example in filteredExamples"
        :key="example.file"
        v-bind="example"
      />
    </div>

    <div class="no-results" v-else>
      <p>No examples match your filters.</p>
      <button @click="selectedComplexity = ''; searchQuery = ''">Clear filters</button>
    </div>
  </div>
</template>

<style scoped>
.example-gallery {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px;
  background: var(--vp-c-bg-soft);
  border-radius: 12px;
  border: 1px solid var(--vp-c-divider);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-group {
  flex: 1;
  min-width: 250px;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--vp-c-text-2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.complexity-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.complexity-btn {
  padding: 8px 14px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-2);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.complexity-btn:hover {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-text-1);
}

.complexity-btn.active {
  background: var(--vp-c-brand-soft);
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}

.complexity-btn.beginner.active {
  background: rgba(34, 197, 94, 0.15);
  border-color: #22c55e;
  color: #22c55e;
}

.complexity-btn.intermediate.active {
  background: rgba(234, 179, 8, 0.15);
  border-color: #eab308;
  color: #eab308;
}

.complexity-btn.advanced.active {
  background: rgba(239, 68, 68, 0.15);
  border-color: #ef4444;
  color: #ef4444;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--vp-c-text-3);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 10px 12px 10px 40px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s ease;
}

.search-input:focus {
  border-color: var(--vp-c-brand-1);
}

.search-input::placeholder {
  color: var(--vp-c-text-3);
}

.results-info {
  font-size: 14px;
  color: var(--vp-c-text-2);
  padding: 0 4px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
  background: var(--vp-c-bg-soft);
  border-radius: 12px;
}

.no-results p {
  margin: 0 0 16px;
  color: var(--vp-c-text-2);
}

.no-results button {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: var(--vp-c-brand-1);
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.no-results button:hover {
  background: var(--vp-c-brand-2);
}

@media (max-width: 640px) {
  .filters {
    flex-direction: column;
  }

  .complexity-filters {
    flex-wrap: wrap;
  }

  .gallery-grid {
    grid-template-columns: 1fr;
  }
}
</style>
