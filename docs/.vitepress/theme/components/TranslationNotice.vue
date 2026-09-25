<script setup>
// Shown on a translated page whose English source changed after it was
// translated (frontmatter.translationStale, set in docs/.vitepress/translations.js).
import { computed } from 'vue'
import { useData, withBase } from 'vitepress'

const { frontmatter, lang } = useData()

const TEXT = {
  'pt-BR': 'Esta tradução pode estar desatualizada: a página em inglês mudou depois dela.',
  es: 'Esta traducción puede estar desactualizada: la página en inglés cambió después de ella.',
  'zh-CN': '此译文可能已过时：英文原文在翻译之后有所更新。',
}
const LINK = { 'pt-BR': 'Ver a versão em inglês', es: 'Ver la versión en inglés', 'zh-CN': '查看英文原文' }

const show = computed(() => frontmatter.value.translationStale === true)
const text = computed(() => TEXT[lang.value] || 'This translation may be out of date.')
const linkText = computed(() => LINK[lang.value] || 'See the English version')
const href = computed(() => withBase(frontmatter.value.englishLink || '/'))
</script>

<template>
  <div v-if="show" class="translation-notice custom-block warning">
    <p>{{ text }} <a :href="href">{{ linkText }}</a></p>
  </div>
</template>

<style scoped>
.translation-notice {
  margin: 0 0 16px;
}
</style>
