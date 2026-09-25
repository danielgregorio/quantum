import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import TranslationNotice from './components/TranslationNotice.vue'
import ExampleCard from './components/ExampleCard.vue'
import ExampleGallery from './components/ExampleGallery.vue'
import ExampleList from './components/ExampleList.vue'
import CategoryCard from './components/CategoryCard.vue'
import './custom.css'
import { tokenize } from '../search-tokenize.js'

export default {
  extends: DefaultTheme,
  // A translation whose English source changed says so, on doc pages and homes.
  Layout: () => h(DefaultTheme.Layout, null, {
    'doc-before': () => h(TranslationNotice),
    'home-hero-before': () => h(TranslationNotice),
  }),
  enhanceApp({ app, siteData }) {
    // The search box splits a query as the index was split (Intl.Segmenter, so
    // Chinese works): the config's tokenize function does not reach the browser.
    const miniSearch = siteData.value.themeConfig?.search?.options?.miniSearch
    if (miniSearch) {
      miniSearch.options = { ...miniSearch.options, tokenize }
      miniSearch.searchOptions = { ...miniSearch.searchOptions, tokenize }
    }

    // Register global components for use in markdown
    app.component('ExampleCard', ExampleCard)
    app.component('ExampleGallery', ExampleGallery)
    app.component('ExampleList', ExampleList)
    app.component('CategoryCard', CategoryCard)
  }
}
