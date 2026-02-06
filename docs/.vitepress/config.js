import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Quantum Framework',
  description: 'Full-stack declarative framework for building web, desktop, and mobile applications',

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'UI Engine', link: '/ui-engine/overview' },
      { text: 'API Reference', link: '/api/' },
      { text: 'Examples', link: '/examples/' },
      { text: 'GitHub', link: 'https://github.com/danielgregorio/quantum' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Quick Start', link: '/guide/quick-start' },
            { text: 'Project Structure', link: '/guide/project-structure' }
          ]
        },
        {
          text: 'Core Concepts',
          items: [
            { text: 'Components (.q files)', link: '/guide/components' },
            { text: 'State Management (q:set)', link: '/guide/state-management' },
            { text: 'Loops (q:loop)', link: '/guide/loops' },
            { text: 'Conditionals (q:if/q:else)', link: '/guide/conditionals' },
            { text: 'Functions (q:function)', link: '/guide/functions' },
            { text: 'Data Binding', link: '/guide/databinding' }
          ]
        },
        {
          text: 'Data & Backend',
          items: [
            { text: 'Database Queries (q:query)', link: '/guide/query' },
            { text: 'Data Import', link: '/guide/data-import' },
            { text: 'Authentication', link: '/guide/authentication' },
            { text: 'Sessions & Scopes', link: '/guide/sessions' }
          ]
        },
        {
          text: 'Web Applications',
          items: [
            { text: 'Applications', link: '/guide/applications' },
            { text: 'Actions & Forms', link: '/guide/actions' },
            { text: 'Email (q:mail)', link: '/guide/email' }
          ]
        }
      ],
      '/ui-engine/': [
        {
          text: 'UI Engine',
          items: [
            { text: 'Overview', link: '/ui-engine/overview' },
            { text: 'Design Tokens', link: '/ui-engine/design-tokens' }
          ]
        },
        {
          text: 'Layout Components',
          items: [
            { text: 'Window', link: '/ui-engine/components/window' },
            { text: 'HBox & VBox', link: '/ui-engine/components/box-layouts' },
            { text: 'Grid', link: '/ui-engine/components/grid' },
            { text: 'Panel', link: '/ui-engine/components/panel' },
            { text: 'Tabs', link: '/ui-engine/components/tabs' },
            { text: 'Accordion', link: '/ui-engine/components/accordion' }
          ]
        },
        {
          text: 'Form Components',
          items: [
            { text: 'Form & FormItem', link: '/ui-engine/components/form' },
            { text: 'Input', link: '/ui-engine/components/input' },
            { text: 'Button', link: '/ui-engine/components/button' },
            { text: 'Checkbox & Switch', link: '/ui-engine/components/checkbox' },
            { text: 'Select & Radio', link: '/ui-engine/components/select' }
          ]
        },
        {
          text: 'Data Components',
          items: [
            { text: 'Table', link: '/ui-engine/components/table' },
            { text: 'List', link: '/ui-engine/components/list' },
            { text: 'Tree', link: '/ui-engine/components/tree' }
          ]
        },
        {
          text: 'Display Components',
          items: [
            { text: 'Text', link: '/ui-engine/components/text' },
            { text: 'Card', link: '/ui-engine/components/card' },
            { text: 'Modal', link: '/ui-engine/components/modal' },
            { text: 'Alert', link: '/ui-engine/components/alert' },
            { text: 'Badge', link: '/ui-engine/components/badge' },
            { text: 'Avatar', link: '/ui-engine/components/avatar' },
            { text: 'Tooltip & Dropdown', link: '/ui-engine/components/tooltip-dropdown' },
            { text: 'Chart', link: '/ui-engine/components/chart' }
          ]
        },
        {
          text: 'Navigation Components',
          items: [
            { text: 'Breadcrumb', link: '/ui-engine/components/breadcrumb' },
            { text: 'Pagination', link: '/ui-engine/components/pagination' },
            { text: 'Menu', link: '/ui-engine/components/menu' }
          ]
        },
        {
          text: 'Features',
          items: [
            { text: 'Animation System', link: '/ui-engine/features/animation' },
            { text: 'Form Validation', link: '/ui-engine/features/validation' },
            { text: 'State Persistence', link: '/ui-engine/features/persistence' },
            { text: 'Theming', link: '/ui-engine/features/theming' }
          ]
        },
        {
          text: 'Targets',
          items: [
            { text: 'HTML Target', link: '/ui-engine/targets/html' },
            { text: 'Desktop (pywebview)', link: '/ui-engine/targets/desktop' },
            { text: 'Mobile (React Native)', link: '/ui-engine/targets/mobile' },
            { text: 'Terminal (Textual)', link: '/ui-engine/targets/terminal' }
          ]
        }
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api/' },
            { text: 'Tags Reference', link: '/api/tags' },
            { text: 'Attributes Reference', link: '/api/attributes' },
            { text: 'Built-in Functions', link: '/api/functions' }
          ]
        }
      ],
      '/examples/': [
        {
          text: 'Examples',
          items: [
            { text: 'Overview', link: '/examples/' },
            { text: 'Basic Components', link: '/examples/basic-components' },
            { text: 'Forms & Validation', link: '/examples/forms' },
            { text: 'Data Queries', link: '/examples/queries' },
            { text: 'UI Applications', link: '/examples/ui-apps' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/danielgregorio/quantum' }
    ],

    footer: {
      message: 'Quantum Framework - Simplicity over configuration',
      copyright: 'MIT Licensed | Built with VitePress'
    },

    search: {
      provider: 'local'
    }
  },

  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark'
    },
    lineNumbers: true
  }
})
