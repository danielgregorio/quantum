import DefaultTheme from 'vitepress/theme'
import ExampleCard from './components/ExampleCard.vue'
import ExampleGallery from './components/ExampleGallery.vue'
import ExampleList from './components/ExampleList.vue'
import CategoryCard from './components/CategoryCard.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // Register global components for use in markdown
    app.component('ExampleCard', ExampleCard)
    app.component('ExampleGallery', ExampleGallery)
    app.component('ExampleList', ExampleList)
    app.component('CategoryCard', CategoryCard)
  }
}
