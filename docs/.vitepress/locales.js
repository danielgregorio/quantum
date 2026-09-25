// The site's languages: English at the root, and /pt/ (pt-BR), /es/ and /zh/
// (zh-CN). This file holds each language's interface text (the "chrome": nav,
// "edit this page", search box...). Page translations live in docs/<lang>/.
//
// Until a page is translated, a language's nav points to the English page, and
// the language switcher goes to the language's home (i18nRouting: false in
// config.js) — a switcher to /pt/guide/x would be a 404 today.

export const LANGUAGES = {
  root: { label: 'English', lang: 'en', prefix: '/' },
  pt: { label: 'Português (Brasil)', lang: 'pt-BR', prefix: '/pt/' },
  es: { label: 'Español', lang: 'es', prefix: '/es/' },
  zh: { label: '简体中文', lang: 'zh-CN', prefix: '/zh/' },
}

const TEXT = {
  root: {
    description: 'Declarative web applications in XML, with AI and RAG built into the language',
    home: 'Home', docs: 'Docs', guide: 'Guide', tutorial: 'Tutorial', cookbook: 'Cookbook', reference: 'Reference',
    spec: 'Specification (SPEC)', showcase: 'Showcase', blog: 'Blog', changelog: 'Changelog',
    status: 'Status', sponsor: 'Sponsor',
    editLink: 'Edit this page on GitHub', lastUpdated: 'Last updated', outline: 'On this page',
    prev: 'Previous page', next: 'Next page', langMenu: 'Change language', returnToTop: 'Return to top',
    sidebarMenu: 'Menu', darkMode: 'Appearance', lightTitle: 'Switch to light theme',
    darkTitle: 'Switch to dark theme', skipToContent: 'Skip to content',
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
    home: 'Início', docs: 'Documentação', guide: 'Guia', tutorial: 'Tutorial', cookbook: 'Receitas', reference: 'Referência',
    spec: 'Especificação (SPEC)', showcase: 'Vitrine', blog: 'Blog', changelog: 'Mudanças',
    status: 'Status', sponsor: 'Apoie',
    editLink: 'Editar esta página no GitHub', lastUpdated: 'Atualizado em', outline: 'Nesta página',
    prev: 'Página anterior', next: 'Próxima página', langMenu: 'Mudar idioma', returnToTop: 'Voltar ao topo',
    sidebarMenu: 'Menu', darkMode: 'Aparência', lightTitle: 'Mudar para o tema claro',
    darkTitle: 'Mudar para o tema escuro', skipToContent: 'Pular para o conteúdo',
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
    home: 'Inicio', docs: 'Documentación', guide: 'Guía', tutorial: 'Tutorial', cookbook: 'Recetario', reference: 'Referencia',
    spec: 'Especificación (SPEC)', showcase: 'Escaparate', blog: 'Blog', changelog: 'Cambios',
    status: 'Estado', sponsor: 'Patrocinar',
    editLink: 'Editar esta página en GitHub', lastUpdated: 'Actualizado', outline: 'En esta página',
    prev: 'Página anterior', next: 'Página siguiente', langMenu: 'Cambiar idioma', returnToTop: 'Volver arriba',
    sidebarMenu: 'Menú', darkMode: 'Apariencia', lightTitle: 'Cambiar al tema claro',
    darkTitle: 'Cambiar al tema oscuro', skipToContent: 'Ir al contenido',
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
    home: '首页', docs: '文档', guide: '指南', tutorial: '教程', cookbook: '实用示例', reference: '参考',
    spec: '规范 (SPEC)', showcase: '案例', blog: '博客', changelog: '更新日志',
    status: '状态', sponsor: '赞助',
    editLink: '在 GitHub 上编辑此页', lastUpdated: '最后更新', outline: '本页内容',
    prev: '上一页', next: '下一页', langMenu: '切换语言', returnToTop: '返回顶部',
    sidebarMenu: '菜单', darkMode: '外观', lightTitle: '切换到浅色主题',
    darkTitle: '切换到深色主题', skipToContent: '跳到正文',
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

// The top nav: Home · Docs (Guide, Tutorial, Reference, SPEC) · Showcase · Blog ·
// Changelog · Status · Sponsor · GitHub. Only the home is per language today.
function nav(key) {
  const t = TEXT[key]
  const home = LANGUAGES[key].prefix
  return [
    { text: t.home, link: home },
    {
      text: t.docs,
      items: [
        { text: t.guide, link: '/guide/getting-started' },
        { text: t.tutorial, link: '/tutorial/' },
        { text: t.cookbook, link: '/cookbook/' },
        { text: t.reference, link: '/reference/' },
        { text: t.spec, link: '/reference/spec' },
      ],
    },
    { text: t.showcase, link: '/showcase/' },
    { text: t.blog, link: '/blog/' },
    { text: t.changelog, link: '/changelog/' },
    { text: t.status, link: '/status/' },
    { text: t.sponsor, link: '/sponsor/' },
  ]
}

function chrome(key) {
  const t = TEXT[key]
  return {
    nav: nav(key),
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
