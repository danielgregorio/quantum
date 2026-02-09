<script setup>
import { computed } from 'vue'

const props = defineProps({
  file: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  complexity: { type: String, default: 'beginner' },
  tags: { type: Array, default: () => [] },
  features: { type: Array, default: () => [] },
  relatedDocs: { type: Array, default: () => [] },
  lineCount: { type: Number, default: 0 }
})

const complexityClass = computed(() => `complexity-${props.complexity}`)

const complexityLabel = computed(() => {
  const labels = {
    beginner: 'Beginner',
    intermediate: 'Intermediate',
    advanced: 'Advanced'
  }
  return labels[props.complexity] || 'Beginner'
})

const sourceUrl = computed(() => {
  return `https://github.com/danielgregorio/quantum/blob/main/examples/${props.file}`
})

const displayTags = computed(() => {
  return props.tags.slice(0, 4)
})
</script>

<template>
  <div class="example-card" :class="complexityClass">
    <div class="card-header">
      <span class="complexity-badge" :class="complexityClass">{{ complexityLabel }}</span>
      <h3 class="card-title">{{ title }}</h3>
    </div>

    <p class="card-description">{{ description }}</p>

    <div class="card-tags" v-if="displayTags.length">
      <span v-for="tag in displayTags" :key="tag" class="tag">{{ tag }}</span>
    </div>

    <div class="card-meta">
      <span class="line-count" v-if="lineCount">{{ lineCount }} lines</span>
      <span class="file-name">{{ file }}</span>
    </div>

    <div class="card-actions">
      <a :href="sourceUrl" target="_blank" rel="noopener" class="btn btn-source">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
        </svg>
        View Source
      </a>
      <a v-if="relatedDocs.length" :href="relatedDocs[0]" class="btn btn-docs">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
        </svg>
        Docs
      </a>
    </div>
  </div>
</template>

<style scoped>
.example-card {
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
}

.example-card:hover {
  border-color: var(--vp-c-brand-1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.complexity-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  width: fit-content;
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

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  line-height: 1.4;
}

.card-description {
  margin: 0;
  font-size: 14px;
  color: var(--vp-c-text-2);
  line-height: 1.5;
  flex-grow: 1;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  background: var(--vp-c-default-soft);
  border-radius: 6px;
  font-size: 12px;
  color: var(--vp-c-text-2);
  font-family: var(--vp-font-family-mono);
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--vp-c-text-3);
}

.file-name {
  font-family: var(--vp-font-family-mono);
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.15s ease;
}

.btn-source {
  background: var(--vp-c-brand-soft);
  color: var(--vp-c-brand-1);
}

.btn-source:hover {
  background: var(--vp-c-brand-1);
  color: white;
}

.btn-docs {
  background: var(--vp-c-default-soft);
  color: var(--vp-c-text-1);
}

.btn-docs:hover {
  background: var(--vp-c-default-3);
}
</style>
