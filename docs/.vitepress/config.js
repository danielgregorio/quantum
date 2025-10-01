import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Quantum Language',
  description: 'Experimental declarative language for components, applications, and jobs',
  
  themeConfig: {
    logo: '/logo.svg',
    
    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Examples', link: '/examples/' },
      { text: 'API', link: '/api/' },
      { text: 'GitHub', link: 'https://github.com/danielgregorio/quantum' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Basic Concepts', link: '/guide/basic-concepts' }
          ]
        },
        {
          text: 'Language Reference',
          items: [
            { text: 'Components', link: '/guide/components' },
            { text: 'Loops', link: '/guide/loops' },
            { text: 'Databinding', link: '/guide/databinding' },
            { text: 'Applications', link: '/guide/applications' }
          ]
        }
      ],
      '/examples/': [
        {
          text: 'Examples',
          items: [
            { text: 'Overview', link: '/examples/' },
            { text: 'Basic Loops', link: '/examples/basic-loops' },
            { text: 'Dynamic Data', link: '/examples/dynamic-data' },
            { text: 'Web Applications', link: '/examples/web-applications' }
          ]
        }
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api/' },
            { text: 'AST Nodes', link: '/api/ast-nodes' },
            { text: 'Parser', link: '/api/parser' },
            { text: 'Runtime', link: '/api/runtime' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/danielgregorio/quantum' }
    ],

    footer: {
      message: 'Quantum Language - Simplicity over configuration',
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