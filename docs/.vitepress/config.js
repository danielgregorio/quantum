import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Quantum Framework',
  description: 'Full-stack declarative framework for building web, desktop, and mobile applications',

  head: [
    ['script', { async: '', src: 'https://www.googletagmanager.com/gtag/js?id=G-7GDMZJJWW0' }],
    ['script', {}, `
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-7GDMZJJWW0');
    `]
  ],

  appearance: 'dark',

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'UI Engine', link: '/ui/overview' },
      { text: 'Features', link: '/features/theming' },
      { text: 'Targets', link: '/targets/html' },
      { text: 'API Reference', link: '/api/tags-reference' },
      { text: 'Extensibility', link: '/extensibility/plugins' },
      { text: 'Tools', link: '/tools/cli' },
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
            { text: 'Data Fetching (q:fetch)', link: '/guide/data-fetching' },
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
      '/ui/': [
        {
          text: 'UI Engine',
          items: [
            { text: 'Overview', link: '/ui/overview' },
            { text: 'Layout', link: '/ui/layout' },
            { text: 'Forms', link: '/ui/forms' },
            { text: 'Data Display', link: '/ui/data-display' },
            { text: 'Feedback', link: '/ui/feedback' },
            { text: 'Navigation', link: '/ui/navigation' },
            { text: 'Overlays', link: '/ui/overlays' },
            { text: 'Advanced Components', link: '/ui/advanced-components' }
          ]
        }
      ],
      '/features/': [
        {
          text: 'Features',
          items: [
            { text: 'Theming', link: '/features/theming' },
            { text: 'Animations', link: '/features/animations' },
            { text: 'Form Validation', link: '/features/form-validation' },
            { text: 'State Persistence', link: '/features/state-persistence' }
          ]
        }
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Tags Reference (q:)', link: '/api/tags-reference' },
            { text: 'UI Reference (ui:)', link: '/api/ui-reference' },
            { text: 'Attributes Reference', link: '/api/attributes-reference' }
          ]
        }
      ],
      '/extensibility/': [
        {
          text: 'Extensibility',
          items: [
            { text: 'Plugin System', link: '/extensibility/plugins' },
            { text: 'Package Manager', link: '/extensibility/packages' }
          ]
        }
      ],
      '/examples/': [
        {
          text: 'Examples Gallery',
          items: [
            { text: 'Overview', link: '/examples/' }
          ]
        },
        {
          text: 'By Feature',
          collapsed: false,
          items: [
            { text: 'State Management', link: '/examples/state-management' },
            { text: 'Loops', link: '/examples/loops' },
            { text: 'Conditionals', link: '/examples/conditionals' },
            { text: 'Functions', link: '/examples/functions' },
            { text: 'Database Queries', link: '/examples/queries' },
            { text: 'Forms & Actions', link: '/examples/forms-actions' },
            { text: 'Authentication', link: '/examples/authentication' },
            { text: 'AI Agents', link: '/examples/agents' },
            { text: 'UI & Theming', link: '/examples/ui-theming' },
            { text: 'Games', link: '/examples/games' },
            { text: 'Data Import', link: '/examples/data-import' },
            { text: 'Advanced', link: '/examples/advanced' }
          ]
        }
      ],
      '/targets/': [
        {
          text: 'Build Targets',
          items: [
            { text: 'HTML Target', link: '/targets/html' },
            { text: 'Desktop (pywebview)', link: '/targets/desktop' },
            { text: 'Mobile (React Native)', link: '/targets/mobile' },
            { text: 'Terminal (Textual)', link: '/targets/terminal' }
          ]
        }
      ],
      '/tools/': [
        {
          text: 'Developer Tools',
          items: [
            { text: 'CLI Commands', link: '/tools/cli' },
            { text: 'Hot Reload', link: '/tools/hot-reload' },
            { text: 'VS Code Extension', link: '/tools/vscode-extension' },
            { text: 'LSP Server', link: '/tools/lsp-server' }
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
  },

  ignoreDeadLinks: true
})
