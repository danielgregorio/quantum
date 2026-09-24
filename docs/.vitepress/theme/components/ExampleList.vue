<script setup>
import { computed } from 'vue'

const props = defineProps({
  examples: { type: Array, required: true },
  limit: { type: Number, default: 5 },
  categoryLink: { type: String, default: '' }
})

const displayedExamples = computed(() => {
  return props.examples.slice(0, props.limit)
})

const hasMore = computed(() => {
  return props.examples.length > props.limit
})

const getSourceUrl = (file) => {
  return `https://github.com/danielgregorio/quantum/blob/main/examples/${file}`
}

const getComplexityClass = (complexity) => {
  return `complexity-${complexity}`
}
</script>

<template>
  <div class="example-list">
    <ul class="examples">
      <li v-for="ex in displayedExamples" :key="ex.file" class="example-item">
        <a :href="getSourceUrl(ex.file)" target="_blank" rel="noopener" class="example-link">
          <span class="example-title">{{ ex.title }}</span>
          <span class="complexity-indicator" :class="getComplexityClass(ex.complexity)">
            {{ ex.complexity }}
          </span>
        </a>
        <p class="example-desc" v-if="ex.description">{{ ex.description }}</p>
      </li>
    </ul>

    <div class="view-more" v-if="hasMore && categoryLink">
      <a :href="categoryLink" class="view-more-link">
        View all {{ examples.length }} examples
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14m-7-7 7 7-7 7"/>
        </svg>
      </a>
    </div>
  </div>
</template>

<style scoped>
.example-list {
  margin: 16px 0;
}

.examples {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.example-item {
  padding: 12px 16px;
  background: var(--vp-c-bg-soft);
  border-radius: 8px;
  border: 1px solid var(--vp-c-divider);
  transition: border-color 0.15s ease;
}

.example-item:hover {
  border-color: var(--vp-c-brand-1);
}

.example-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-decoration: none;
  color: var(--vp-c-text-1);
}

.example-title {
  font-weight: 500;
}

.example-link:hover .example-title {
  color: var(--vp-c-brand-1);
}

.complexity-indicator {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 10px;
}

.complexity-beginner {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.complexity-intermediate {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.complexity-advanced {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.example-desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--vp-c-text-2);
  line-height: 1.5;
}

.view-more {
  margin-top: 16px;
}

.view-more-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--vp-c-brand-1);
  font-weight: 500;
  text-decoration: none;
}

.view-more-link:hover {
  text-decoration: underline;
}
</style>
