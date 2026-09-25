// Replaces the default theme's composables/langs.js (aliased in config.js), so
// the language switcher goes to the same page in the other language when that
// page is translated, and to the language's home otherwise. VitePress's own
// i18nRouting would link the same path in every language and 404 on the pages
// a language has not translated; this reads which pages exist from
// themeConfig.translatedPaths, built from TRANSLATED in locales.js.
// Same API as VitePress 1.6.4's useLangs: { localeLinks, currentLang }.
import { computed } from 'vue'
import { useData } from 'vitepress'

export function useLangs({ correspondingLink = false } = {}) {
  const { site, localeIndex, page, theme, hash } = useData()

  const currentLang = computed(() => ({
    label: site.value.locales[localeIndex.value]?.label,
    link: site.value.locales[localeIndex.value]?.link ||
      (localeIndex.value === 'root' ? '/' : `/${localeIndex.value}/`),
  }))

  const localeLinks = computed(() => Object.entries(site.value.locales).flatMap(([key, value]) => {
    if (currentLang.value.label === value.label) return []
    const home = value.link || (key === 'root' ? '/' : `/${key}/`)
    const route = englishRoute(page.value.relativePath, currentLang.value.link)
    const target = correspondingLink ? samePage(theme.value.translatedPaths || {}, key, route) : null
    return {
      text: value.label,
      link: (target === null ? home : withExtension(home.replace(/\/$/, '') + target, !site.value.cleanUrls)) + hash.value,
    }
  }))

  return { localeLinks, currentLang }
}

// "pt/guide/loops.md" on the pt locale -> "/guide/loops"; "pt/cookbook/index.md" -> "/cookbook/".
function englishRoute(relativePath, localeLink) {
  const path = relativePath.slice(localeLink.length - 1)
  return '/' + path.replace(/(^|\/)index\.md$/, '$1').replace(/\.md$/, '')
}

// The route in language `key`, or null when that language does not have the page.
// English (root) has every page a translation comes from.
function samePage(translated, key, route) {
  if (key === 'root') return route
  return (translated[key] || []).includes(route) ? route : null
}

function withExtension(link, addExt) {
  return addExt && !link.endsWith('/') ? link + '.html' : link
}
