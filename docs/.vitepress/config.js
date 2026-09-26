import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'
import { LANGUAGES, guideSidebar, locales, searchLocales } from './locales.js'
import { tokenize } from './search-tokenize.js'
import { ariaLabelsInHtml } from './theme/aria-labels.js'
import { markStaleTranslation } from './translations.js'
import { translatedPaths } from './translated-paths.js'

// Served at the root of https://quantumframework.net (GitHub Pages with a
// custom domain). Whoever serves it under a sub-path passes DOCS_BASE, and on
// another host DOCS_HOST (the absolute URLs of hreflang, the sitemap and Open
// Graph). Nothing else in the site may spell the base path: links are relative
// or go through it.
const BASE = process.env.DOCS_BASE || '/'
const HOST = (process.env.DOCS_HOST || 'https://quantumframework.net').replace(/\/$/, '')
const SITE = HOST + BASE
const DOCS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const LOCALES = locales()

// The URL of a page (its .md path under docs/), as VitePress builds it.
function route(relativePath) {
  return relativePath.replace(/(^|\/)index\.md$/, '$1').replace(/\.md$/, '.html')
}

// hreflang: the same page in each language it exists in (SEO), and English as
// the default. A page not translated yet has no alternate for that language.
function alternates(relativePath) {
  const current = Object.values(LANGUAGES).find(l => l.prefix !== '/' && relativePath.startsWith(l.prefix.slice(1)))
  const stem = current ? relativePath.slice(current.prefix.length - 1) : relativePath
  const links = []
  for (const language of Object.values(LANGUAGES)) {
    const file = (language.prefix === '/' ? '' : language.prefix.slice(1)) + stem
    if (fs.existsSync(path.join(DOCS, file))) {
      links.push(['link', { rel: 'alternate', hreflang: language.lang, href: SITE + route(file) }])
    }
  }
  if (links.length > 1) {
    links.push(['link', { rel: 'alternate', hreflang: 'x-default', href: SITE + route(stem) }])
  }
  return links
}

// Open Graph: the language's image (scripts/site/og-images.py writes them).
function openGraph(pageData, siteTitle) {
  const language = Object.entries(LANGUAGES).find(([key, l]) => key !== 'root' && pageData.relativePath.startsWith(l.prefix.slice(1)))
  const key = language ? language[0] : 'root'
  const title = pageData.title ? `${pageData.title} | ${siteTitle}` : siteTitle
  const description = pageData.description || pageData.frontmatter?.description || ''
  return [
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: title }],
    ...(description ? [['meta', { property: 'og:description', content: description }]] : []),
    ['meta', { property: 'og:url', content: SITE + route(pageData.relativePath) }],
    ['meta', { property: 'og:image', content: `${SITE}og/${key === 'root' ? 'en' : key}.png` }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
  ]
}

export default defineConfig({
  base: BASE,

  // Pages kept in the repository but not published: their code does not
  // work with Quantum 1.0, and the Cookbook (tested recipes) replaces them.
  // They are rewritten there, not patched here. tests/docs/docs_blocks.py
  // lists them as under review.
  srcExclude: [
    'examples/advanced.md', 'examples/agents.md', 'examples/authentication.md',
    'examples/conditionals.md', 'examples/data-import.md', 'examples/forms-actions.md',
    'examples/functions.md', 'examples/games.md', 'examples/loops.md',
    'examples/queries.md', 'examples/state-management.md', 'examples/ui-theming.md',
    'features/animations.md', 'features/form-validation.md', 'features/theming.md',
    // Old notes linked from no menu, that the site presented as current: a
    // benchmark nothing reproduces ("faster than PHP and Python"), the q:query
    // implementation plan (src/ paths, attributes since removed) and the
    // performance-phase notes (caches, "fully compatible with PyPy", untested).
    'benchmarks/performance-comparison.md', 'architecture/query-implementation.md',
    'internals/ast-cache.md', 'internals/expression-cache.md', 'internals/pypy-compatibility.md',
  ],

  title: 'Quantum Framework',
  description: 'Declarative web applications in XML, with AI and RAG built into the language',

  // Cloudflare Web Analytics: no cookies, no personal data. The DNS is not
  // proxied (GitHub Pages serves the site), so the beacon is in the page; its
  // token is public by design.
  head: [
    ['script', {
      defer: '',
      src: 'https://static.cloudflareinsights.com/beacon.min.js',
      'data-cf-beacon': '{"token": "1b8965ae430c43f49739c6c9b5b49856"}',
    }],
  ],

  appearance: 'dark',

  // English at the root; /pt/, /es/ and /zh/ (docs/.vitepress/locales.js).
  locales: LOCALES,

  sitemap: { hostname: SITE },

  // BEGIN translations (docs/.vitepress/translations.js): a translated page
  // whose English source changed after it was translated is marked stale.
  transformPageData(pageData) {
    markStaleTranslation(pageData, DOCS)
  },
  // END translations

  // Screen-reader labels in the page's language in the built HTML too
  // (theme/aria-labels.js); the theme sets them again after each navigation.
  transformHtml(html, _id, { pageData }) {
    const key = Object.keys(LANGUAGES).find(k => k !== 'root' && pageData.relativePath.startsWith(k + '/')) || 'root'
    return ariaLabelsInHtml(html, LOCALES[key].themeConfig.ariaLabels)
  },

  transformHead({ pageData, siteData }) {
    return [...alternates(pageData.relativePath), ...openGraph(pageData, siteData.title)]
  },

  // The language switcher (theme/langs.js replaces the default theme's
  // composables/langs.js): the same page in the other language when it exists.
  vite: {
    resolve: {
      alias: [{
        find: /^\.{1,2}\/composables\/langs(\.js)?$/,
        replacement: fileURLToPath(new URL('./theme/langs.js', import.meta.url)),
      }],
    },
  },

  themeConfig: {
    translatedPaths: translatedPaths(DOCS),
    logo: '/logo.svg',

    // Until the pages are translated (wave 2), the language switcher goes to the
    // language's home instead of the same page in that language (a 404 today).
    i18nRouting: false,

    sidebar: {
      // One table for every language (docs/.vitepress/locales.js).
      '/guide/': guideSidebar('root'),
      // BEGIN Reference (generated pages: scripts/generate-reference.py)
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'Overview', link: '/reference/' },
            { text: 'Tags', link: '/reference/tags' },
            { text: 'Expression functions', link: '/reference/functions' },
            { text: 'Command line', link: '/reference/cli' },
            { text: 'Configuration', link: '/reference/config' },
            { text: 'UI tags (ui:)', link: '/reference/ui' },
            { text: 'Specification', link: '/reference/spec' },
            { text: 'Experimental tags', link: '/reference/experimental' }
          ]
        }
      ],
      // END Reference
      '/targets/': [
        {
          text: 'Build Targets',
          items: [
            { text: 'Desktop (quantum desktop)', link: '/targets/desktop' }
          ]
        }
      ],
      '/tools/': [
        {
          text: 'Developer Tools',
          items: [
            { text: 'CLI Commands', link: '/tools/cli' },
            { text: 'Hot Reload', link: '/tools/hot-reload' },
            { text: 'The /_dev Panel', link: '/tools/dev-panel' },
            { text: 'Error Pages', link: '/tools/error-pages' },
            { text: 'quantum check', link: '/tools/check' },
            { text: 'VS Code Extension', link: '/tools/vscode-extension' },
            { text: 'LSP Server', link: '/tools/lsp-server' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/danielgregorio/quantum' }
    ],

    search: {
      provider: 'local',
      options: {
        locales: searchLocales(),
        // Chinese has no spaces between words: split with Intl.Segmenter when
        // the index is built. The browser gets the same function from
        // theme/index.js (functions do not survive into the client config).
        miniSearch: { options: { tokenize }, searchOptions: { tokenize } }
      }
    }
  },

  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark'
    },
    lineNumbers: true
  },

  // A link to a page that does not exist fails the build (CI builds the docs
  // on every push; see the `docs` job in .github/workflows/ci.yml).
  ignoreDeadLinks: false
})
