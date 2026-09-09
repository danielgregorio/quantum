<script setup>
defineProps({
  id: { type: String, required: true },
  name: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: String, default: '' },
  docsPath: { type: String, default: '' },
  exampleCount: { type: Number, default: 0 }
})
</script>

<template>
  <a :href="`/examples/${id}`" class="category-card">
    <div class="card-icon">{{ icon }}</div>
    <div class="card-content">
      <h3 class="card-title">{{ name }}</h3>
      <p class="card-description">{{ description }}</p>
      <div class="card-footer">
        <span class="example-count">{{ exampleCount }} examples</span>
        <span class="arrow">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14m-7-7 7 7-7 7"/>
          </svg>
        </span>
      </div>
    </div>
  </a>
</template>

<style scoped>
.category-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s ease;
}

.category-card:hover {
  border-color: var(--vp-c-brand-1);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-icon {
  font-size: 32px;
  line-height: 1;
  flex-shrink: 0;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--vp-c-text-1);
}

.category-card:hover .card-title {
  color: var(--vp-c-brand-1);
}

.card-description {
  margin: 0;
  font-size: 14px;
  color: var(--vp-c-text-2);
  line-height: 1.5;
  flex-grow: 1;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.example-count {
  font-size: 13px;
  color: var(--vp-c-text-3);
  font-weight: 500;
}

.arrow {
  color: var(--vp-c-text-3);
  transition: transform 0.15s ease;
}

.category-card:hover .arrow {
  color: var(--vp-c-brand-1);
  transform: translateX(4px);
}
</style>
