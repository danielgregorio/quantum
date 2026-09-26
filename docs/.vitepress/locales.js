// The site's languages: English at the root, and /pt/ (pt-BR), /es/ and /zh/
// (zh-CN). This file holds each language's interface text (the "chrome": nav,
// "edit this page", search box...). Page translations live in docs/<lang>/.
//
// Until a page is translated, a language's nav points to the English page, and
// the language switcher goes to the same page in the other language when it is
// translated, and to the language's home otherwise (theme/langs.js, with
// i18nRouting: false in config.js, so it never links a page that does not exist).

export const LANGUAGES = {
  root: { label: 'English', lang: 'en', prefix: '/' },
  pt: { label: 'Português (Brasil)', lang: 'pt-BR', prefix: '/pt/' },
  es: { label: 'Español', lang: 'es', prefix: '/es/' },
  zh: { label: '简体中文', lang: 'zh-CN', prefix: '/zh/' },
}

const TEXT = {
  root: {
    description: 'Declarative web applications in XML, with AI and RAG built into the language',
    playground: 'Playground', home: 'Home', docs: 'Docs', guide: 'Guide', tutorial: 'Tutorial', cookbook: 'Cookbook', stability: 'Stability', reference: 'Reference',
    spec: 'Specification (SPEC)', showcase: 'Showcase', blog: 'Blog', changelog: 'Changelog',
    status: 'Status', sponsor: 'Sponsor', roadmap: 'Roadmap', community: 'Community',
    editLink: 'Edit this page on GitHub', lastUpdated: 'Last updated', outline: 'On this page',
    prev: 'Previous page', next: 'Next page', langMenu: 'Change language', returnToTop: 'Return to top',
    sidebarMenu: 'Menu', darkMode: 'Appearance', lightTitle: 'Switch to light theme',
    darkTitle: 'Switch to dark theme', skipToContent: 'Skip to content',
    mainNavLabel: 'Main Navigation', sidebarNavLabel: 'Sidebar Navigation', pagerLabel: 'Pager',
    notFound: { title: 'PAGE NOT FOUND', quote: 'This page does not exist (yet).', link: 'Take me home' },
    footer: 'MIT Licensed · Built with VitePress',
    search: {
      button: 'Search', placeholder: 'Search the docs', noResults: 'No results for',
      reset: 'Clear the query', back: 'Close search', select: 'to select', navigate: 'to navigate',
      close: 'to close',
    },
  },
  pt: {
    description: 'Aplicações web declarativas em XML, com IA e RAG na própria linguagem',
    playground: 'Playground', home: 'Início', docs: 'Documentação', guide: 'Guia', tutorial: 'Tutorial', cookbook: 'Receitas', stability: 'Estabilidade', reference: 'Referência (em inglês)',
    spec: 'Especificação — SPEC (em inglês)', showcase: 'Vitrine', blog: 'Blog', changelog: 'Mudanças (em inglês)',
    status: 'Status', sponsor: 'Apoie', roadmap: 'Roadmap', community: 'Comunidade',
    editLink: 'Editar esta página no GitHub', lastUpdated: 'Atualizado em', outline: 'Nesta página',
    prev: 'Página anterior', next: 'Próxima página', langMenu: 'Mudar idioma', returnToTop: 'Voltar ao topo',
    sidebarMenu: 'Menu', darkMode: 'Aparência', lightTitle: 'Mudar para o tema claro',
    darkTitle: 'Mudar para o tema escuro', skipToContent: 'Pular para o conteúdo',
    mainNavLabel: 'Navegação principal', sidebarNavLabel: 'Navegação lateral', pagerLabel: 'Página anterior e próxima',
    notFound: { title: 'PÁGINA NÃO ENCONTRADA', quote: 'Esta página não existe (ainda).', link: 'Voltar ao início' },
    footer: 'Licença MIT · Feito com VitePress',
    search: {
      button: 'Buscar', placeholder: 'Buscar na documentação', noResults: 'Nenhum resultado para',
      reset: 'Limpar a busca', back: 'Fechar a busca', select: 'para escolher', navigate: 'para navegar',
      close: 'para fechar',
    },
  },
  es: {
    description: 'Aplicaciones web declarativas en XML, con IA y RAG en el propio lenguaje',
    playground: 'Playground', home: 'Inicio', docs: 'Documentación', guide: 'Guía', tutorial: 'Tutorial', cookbook: 'Recetario', stability: 'Estabilidad', reference: 'Referencia (en inglés)',
    spec: 'Especificación — SPEC (en inglés)', showcase: 'Escaparate', blog: 'Blog', changelog: 'Cambios (en inglés)',
    status: 'Estado', sponsor: 'Patrocinar', roadmap: 'Hoja de ruta', community: 'Comunidad',
    editLink: 'Editar esta página en GitHub', lastUpdated: 'Actualizado', outline: 'En esta página',
    prev: 'Página anterior', next: 'Página siguiente', langMenu: 'Cambiar idioma', returnToTop: 'Volver arriba',
    sidebarMenu: 'Menú', darkMode: 'Apariencia', lightTitle: 'Cambiar al tema claro',
    darkTitle: 'Cambiar al tema oscuro', skipToContent: 'Ir al contenido',
    mainNavLabel: 'Navegación principal', sidebarNavLabel: 'Navegación lateral', pagerLabel: 'Página anterior y siguiente',
    notFound: { title: 'PÁGINA NO ENCONTRADA', quote: 'Esta página no existe (todavía).', link: 'Volver al inicio' },
    footer: 'Licencia MIT · Hecho con VitePress',
    search: {
      button: 'Buscar', placeholder: 'Buscar en la documentación', noResults: 'Sin resultados para',
      reset: 'Borrar la búsqueda', back: 'Cerrar la búsqueda', select: 'para elegir', navigate: 'para navegar',
      close: 'para cerrar',
    },
  },
  zh: {
    description: '用 XML 编写的声明式 Web 应用，语言内置 AI 与 RAG',
    playground: '在线试用', home: '首页', docs: '文档', guide: '指南', tutorial: '教程', cookbook: '实用示例', stability: '稳定性', reference: '参考（英文）',
    spec: '规范 SPEC（英文）', showcase: '案例', blog: '博客', changelog: '更新日志（英文）',
    status: '状态', sponsor: '赞助', roadmap: '路线图', community: '社区',
    editLink: '在 GitHub 上编辑此页', lastUpdated: '最后更新', outline: '本页内容',
    prev: '上一页', next: '下一页', langMenu: '切换语言', returnToTop: '返回顶部',
    sidebarMenu: '菜单', darkMode: '外观', lightTitle: '切换到浅色主题',
    darkTitle: '切换到深色主题', skipToContent: '跳到正文',
    mainNavLabel: '主导航', sidebarNavLabel: '侧边栏导航', pagerLabel: '上一页和下一页',
    notFound: { title: '页面未找到', quote: '此页面（暂时）不存在。', link: '返回首页' },
    footer: 'MIT 许可证 · 使用 VitePress 构建',
    search: {
      button: '搜索', placeholder: '搜索文档', noResults: '没有结果：',
      reset: '清除查询', back: '关闭搜索', select: '选择', navigate: '切换',
      close: '关闭',
    },
  },
}

const GITHUB = 'https://github.com/danielgregorio/quantum'

// The pages each language has translated (docs/<lang>/<path>). The nav links
// to the translation when there is one, and to the English page otherwise.
export const TRANSLATED = {
  pt: ['/guide/why-quantum', '/guide/installation', '/guide/quick-start', '/stability/', '/sponsor/', '/roadmap/', '/tutorial/', '/tutorial/tasks-app', '/cookbook/', '/showcase/', '/examples/',
    '/tools/cli', '/tools/hot-reload', '/tools/dev-panel', '/tools/error-pages', '/tools/check', '/tools/vscode-extension', '/tools/lsp-server', '/targets/desktop',
    '/guide/getting-started', '/guide/components', '/guide/how-a-page-runs', '/guide/state-management', '/guide/loops',
    '/guide/conditionals', '/guide/functions', '/guide/databinding', '/guide/actions', '/guide/query',
    '/guide/authentication', '/guide/ui', '/guide/testing',
    '/guide/ai', '/guide/files-and-mail', '/guide/data-import', '/guide/services', '/guide/sessions',
    '/guide/admin', '/guide/project-structure', '/guide/applications',
    '/blog/', '/status/', '/community/'],
  es: ['/guide/why-quantum', '/guide/installation', '/guide/quick-start', '/stability/', '/sponsor/', '/roadmap/', '/tutorial/', '/tutorial/tasks-app', '/cookbook/', '/showcase/', '/community/', '/tools/cli', '/tools/hot-reload', '/tools/dev-panel', '/tools/error-pages', '/tools/check', '/tools/vscode-extension', '/tools/lsp-server', '/targets/desktop', '/examples/',
    '/blog/', '/status/',
    '/guide/getting-started', '/guide/components', '/guide/how-a-page-runs', '/guide/state-management',
    '/guide/loops', '/guide/conditionals', '/guide/functions', '/guide/databinding',
    '/guide/actions', '/guide/query', '/guide/authentication', '/guide/ui', '/guide/testing',
    '/guide/ai', '/guide/files-and-mail', '/guide/data-import', '/guide/services', '/guide/sessions',
    '/guide/admin', '/guide/project-structure', '/guide/applications'],
  zh: ['/guide/why-quantum', '/guide/installation', '/guide/quick-start', '/stability/', '/sponsor/', '/cookbook/', '/roadmap/', '/tutorial/', '/tutorial/tasks-app', '/showcase/', '/community/', '/tools/cli', '/tools/hot-reload', '/tools/dev-panel', '/tools/error-pages', '/tools/check', '/tools/vscode-extension', '/tools/lsp-server', '/targets/desktop', '/examples/',
    '/blog/', '/status/',
    '/guide/getting-started', '/guide/components', '/guide/how-a-page-runs', '/guide/state-management',
    '/guide/ai', '/guide/files-and-mail', '/guide/data-import', '/guide/services', '/guide/sessions',
    '/guide/admin', '/guide/project-structure', '/guide/applications',
    '/guide/loops', '/guide/conditionals', '/guide/functions', '/guide/databinding',
    '/guide/actions', '/guide/query', '/guide/authentication', '/guide/ui', '/guide/testing'],
}

function link(key, path) {
  return (TRANSLATED[key] || []).includes(path) ? LANGUAGES[key].prefix + path.slice(1) : path
}

// The guide's sidebar, the same for every language: [label key, path]. Each
// item links to the translated page when TRANSLATED lists it (link()), and to
// the English page otherwise. Labels come from GUIDE_TEXT[lang], else English.
const GUIDE_SIDEBAR = [
  ['gettingStarted', [
    ['introduction', '/guide/getting-started'], ['whyQuantum', '/guide/why-quantum'],
    ['installation', '/guide/installation'], ['quickStart', '/guide/quick-start'],
    ['projectStructure', '/guide/project-structure'],
  ]],
  ['coreConcepts', [
    ['components', '/guide/components'], ['howAPageRuns', '/guide/how-a-page-runs'],
    ['stateManagement', '/guide/state-management'], ['loops', '/guide/loops'],
    ['conditionals', '/guide/conditionals'], ['functions', '/guide/functions'],
    ['dataBinding', '/guide/databinding'],
  ]],
  ['ai', [['llmRagAgents', '/guide/ai']]],
  ['dataBackend', [
    ['queries', '/guide/query'], ['dataImport', '/guide/data-import'],
    ['filesAndMail', '/guide/files-and-mail'], ['authentication', '/guide/authentication'],
    ['sessions', '/guide/sessions'], ['services', '/guide/services'], ['admin', '/guide/admin'],
  ]],
  ['webApplications', [
    ['actions', '/guide/actions'], ['testing', '/guide/testing'],
    ['ui', '/guide/ui'], ['applications', '/guide/applications'],
  ]],
]

const GUIDE_TEXT = {
  root: {
    gettingStarted: 'Getting Started', introduction: 'Introduction', whyQuantum: 'Why Quantum',
    installation: 'Installation', quickStart: 'Quick Start', projectStructure: 'Project Structure',
    coreConcepts: 'Core Concepts', components: 'Components (.q files)', howAPageRuns: 'How a Page Runs',
    stateManagement: 'State Management (q:set)', loops: 'Loops (q:loop)',
    conditionals: 'Conditionals (q:if/q:else)', functions: 'Functions (q:function)', dataBinding: 'Data Binding',
    ai: 'AI', llmRagAgents: 'LLM, RAG & Agents',
    dataBackend: 'Data & Backend', queries: 'Database Queries (q:query)', dataImport: 'Data Import',
    filesAndMail: 'Files and Mail', authentication: 'Authentication', sessions: 'Sessions & Scopes',
    services: 'Declared Services', admin: 'Quantum Admin',
    webApplications: 'Web Applications', actions: 'Actions & Forms', testing: 'Testing an App (quantum test)',
    ui: 'One App, Many Screens (ui:)', applications: 'q:application (not for web)',
  },
  es: {
    gettingStarted: 'Primeros pasos', introduction: 'Introducción', whyQuantum: 'Por qué Quantum',
    installation: 'Instalación', quickStart: 'Inicio rápido', projectStructure: 'Estructura del proyecto',
    coreConcepts: 'Conceptos básicos', components: 'Componentes (archivos .q)', howAPageRuns: 'Cómo se ejecuta una página',
    stateManagement: 'Manejo de estado (q:set)', loops: 'Bucles (q:loop)',
    conditionals: 'Condicionales (q:if/q:else)', functions: 'Funciones (q:function)', dataBinding: 'Enlace de datos',
    ai: 'IA', llmRagAgents: 'LLM, RAG y agentes',
    dataBackend: 'Datos y backend', queries: 'Consultas a la base de datos (q:query)', dataImport: 'Importación de datos',
    filesAndMail: 'Archivos y correo', authentication: 'Autenticación', sessions: 'Sesiones y ámbitos',
    services: 'Servicios declarados', admin: 'Quantum Admin',
    webApplications: 'Aplicaciones web', actions: 'Acciones y formularios', testing: 'Probar una aplicación (quantum test)',
    ui: 'Una aplicación, varias pantallas (ui:)', applications: 'q:application (no para la web)',
  },
  pt: {
    gettingStarted: 'Primeiros passos', introduction: 'Introdução', whyQuantum: 'Por que Quantum',
    installation: 'Instalação', quickStart: 'Início rápido', projectStructure: 'Estrutura do projeto',
    coreConcepts: 'Conceitos principais', components: 'Componentes (arquivos .q)', howAPageRuns: 'Como uma página roda',
    stateManagement: 'Gerenciamento de estado (q:set)', loops: 'Loops (q:loop)',
    conditionals: 'Condicionais (q:if/q:else)', functions: 'Funções (q:function)', dataBinding: 'Databinding',
    ai: 'IA', llmRagAgents: 'LLM, RAG e agentes',
    dataBackend: 'Dados e backend', queries: 'Consultas ao banco (q:query)', dataImport: 'Importação de dados',
    filesAndMail: 'Arquivos e e-mail', authentication: 'Autenticação', sessions: 'Sessões e escopos',
    services: 'Serviços declarados', admin: 'Quantum Admin',
    webApplications: 'Aplicações web', actions: 'Ações e formulários', testing: 'Testar uma aplicação (quantum test)',
    ui: 'Uma aplicação, várias telas (ui:)', applications: 'q:application (não para web)',
  },
  zh: {
    gettingStarted: '入门', introduction: '简介', whyQuantum: '为什么选择 Quantum',
    installation: '安装', quickStart: '快速开始', projectStructure: '项目结构',
    coreConcepts: '核心概念', components: '组件（.q 文件）', howAPageRuns: '页面如何运行',
    stateManagement: '状态管理（q:set）', loops: '循环（q:loop）',
    conditionals: '条件（q:if/q:else）', functions: '函数（q:function）', dataBinding: '数据绑定',
    ai: 'AI', llmRagAgents: 'LLM、RAG 与智能体',
    dataBackend: '数据与后端', queries: '数据库查询（q:query）', dataImport: '数据导入',
    filesAndMail: '文件和邮件', authentication: '身份认证', sessions: '会话与作用域',
    services: '声明式服务', admin: 'Quantum Admin',
    webApplications: 'Web 应用', actions: '动作与表单', testing: '测试应用（quantum test）',
    ui: '一个应用，多种界面（ui:）', applications: 'q:application（非 Web）',
  },
}

// BEGIN Tools and targets sidebars (translated pages: docs/<lang>/tools/, docs/<lang>/targets/)
const TOOLS_SIDEBAR = {
  tools: ['tools', [['cli', '/tools/cli'], ['hotReload', '/tools/hot-reload'], ['devPanel', '/tools/dev-panel'],
    ['errorPages', '/tools/error-pages'], ['check', '/tools/check'], ['vscode', '/tools/vscode-extension'],
    ['lsp', '/tools/lsp-server']]],
  targets: ['targets', [['desktop', '/targets/desktop']]],
}

const TOOLS_TEXT = {
  root: {
    tools: 'Developer Tools', targets: 'Build Targets', cli: 'CLI Commands', hotReload: 'Hot Reload',
    devPanel: 'The /_dev Panel', errorPages: 'Error Pages', check: 'quantum check',
    vscode: 'VS Code Extension', lsp: 'LSP Server', desktop: 'Desktop (quantum desktop)',
  },
  pt: {
    tools: 'Ferramentas de desenvolvimento', targets: 'Destinos de build', cli: 'Comandos da CLI',
    hotReload: 'Hot Reload', devPanel: 'O painel /_dev', errorPages: 'Páginas de erro',
    check: 'quantum check', vscode: 'Extensão do VS Code', lsp: 'Servidor LSP',
    desktop: 'Desktop (quantum desktop)',
  },
  es: {
    tools: 'Herramientas de desarrollo', targets: 'Destinos de compilación', cli: 'Comandos de la CLI',
    hotReload: 'Hot Reload', devPanel: 'El panel /_dev', errorPages: 'Páginas de error',
    check: 'quantum check', vscode: 'Extensión de VS Code', lsp: 'Servidor LSP',
    desktop: 'Escritorio (quantum desktop)',
  },
  zh: {
    tools: '开发工具', targets: '构建目标', cli: 'CLI 命令', hotReload: '热重载',
    devPanel: '/_dev 面板', errorPages: '错误页面', check: 'quantum check',
    vscode: 'VS Code 扩展', lsp: 'LSP 服务器', desktop: '桌面（quantum desktop）',
  },
}

export function toolsSidebar(key, section) {
  const t = { ...TOOLS_TEXT.root, ...(TOOLS_TEXT[key] || {}) }
  const [group, items] = TOOLS_SIDEBAR[section]
  return [{
    text: t[group],
    items: items.map(([label, path]) => ({ text: t[label], link: key === 'root' ? path : link(key, path) })),
  }]
}
// END Tools and targets sidebars

export function guideSidebar(key) {
  const t = { ...GUIDE_TEXT.root, ...(GUIDE_TEXT[key] || {}) }
  return GUIDE_SIDEBAR.map(([group, items]) => ({
    text: t[group],
    items: items.map(([label, path]) => ({ text: t[label], link: key === 'root' ? path : link(key, path) })),
  }))
}

// The top nav: Home · Docs (Guide, Tutorial, Reference, SPEC) · Playground · Showcase · Blog ·
// Changelog · Status · Roadmap · Community · Sponsor · GitHub. An entry goes to the
// language's page when TRANSLATED lists it, and to the English page otherwise.
function nav(key) {
  const t = TEXT[key]
  const home = LANGUAGES[key].prefix
  return [
    { text: t.home, link: home },
    {
      text: t.docs,
      items: [
        { text: t.guide, link: link(key, '/guide/getting-started') },
        { text: t.tutorial, link: link(key, '/tutorial/') },
        { text: t.cookbook, link: link(key, '/cookbook/') },
        { text: t.reference, link: link(key, '/reference/') },
        { text: t.spec, link: link(key, '/reference/spec') },
        { text: t.stability, link: link(key, '/stability/') },
      ],
    },
    { text: t.playground, link: '/playground/' },
    { text: t.showcase, link: link(key, '/showcase/') },
    { text: t.blog, link: link(key, '/blog/') },
    { text: t.changelog, link: '/changelog/' },
    { text: t.status, link: link(key, '/status/') },
    { text: t.roadmap, link: link(key, '/roadmap/') },
    { text: t.community, link: link(key, '/community/') },
    { text: t.sponsor, link: link(key, '/sponsor/') },
  ]
}

function chrome(key) {
  const t = TEXT[key]
  return {
    nav: nav(key),
    ...(key === 'root' ? {} : { sidebar: {
      [`${LANGUAGES[key].prefix}guide/`]: guideSidebar(key),
      [`${LANGUAGES[key].prefix}tools/`]: toolsSidebar(key, 'tools'),
      [`${LANGUAGES[key].prefix}targets/`]: toolsSidebar(key, 'targets'),
    } }),
    editLink: { pattern: `${GITHUB}/edit/main/docs/:path`, text: t.editLink },
    lastUpdated: { text: t.lastUpdated },
    outline: { label: t.outline },
    docFooter: { prev: t.prev, next: t.next },
    langMenuLabel: t.langMenu,
    returnToTopLabel: t.returnToTop,
    sidebarMenuLabel: t.sidebarMenu,
    darkModeSwitchLabel: t.darkMode,
    lightModeSwitchTitle: t.lightTitle,
    darkModeSwitchTitle: t.darkTitle,
    skipToContentLabel: t.skipToContent,
    // Screen-reader labels VitePress 1.6.4 writes in English; theme/index.js sets
    // them in the page's language, by the id of the element that holds each.
    ariaLabels: {
      'main-nav-aria-label': t.mainNavLabel,
      'sidebar-aria-label': t.sidebarNavLabel,
      'doc-footer-aria-label': t.pagerLabel,
    },
    notFound: { title: t.notFound.title, quote: t.notFound.quote, linkText: t.notFound.link },
    footer: { message: t.footer, copyright: 'Quantum Framework' },
  }
}

// VitePress `locales`: the root keeps the site-wide themeConfig (sidebar...).
export function locales() {
  const out = {}
  for (const [key, language] of Object.entries(LANGUAGES)) {
    out[key] = {
      label: language.label,
      lang: language.lang,
      description: TEXT[key].description,
      ...(key === 'root' ? {} : { link: language.prefix }),
      themeConfig: chrome(key),
    }
  }
  return out
}

// The search box's own text, per language (search.options.locales).
export function searchLocales() {
  const out = {}
  for (const key of Object.keys(LANGUAGES)) {
    const s = TEXT[key].search
    out[key] = {
      placeholder: s.placeholder,
      translations: {
        button: { buttonText: s.button, buttonAriaLabel: s.button },
        modal: {
          displayDetails: s.button,
          resetButtonTitle: s.reset,
          backButtonTitle: s.back,
          noResultsText: s.noResults,
          footer: {
            selectText: s.select, navigateText: s.navigate, closeText: s.close,
            selectKeyAriaLabel: 'Enter', navigateUpKeyAriaLabel: '↑',
            navigateDownKeyAriaLabel: '↓', closeKeyAriaLabel: 'Esc',
          },
        },
      },
    }
  }
  return out
}
