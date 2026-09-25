// VitePress 1.6.4 writes three screen-reader labels in English ("Main
// Navigation", "Sidebar Navigation", "Pager"). labels is themeConfig.ariaLabels
// of the page's language (locales.js): { element id: text }. An element that is
// not on the page is skipped; this never throws.
export function applyAriaLabels(doc, labels) {
  if (!doc || !labels) return
  for (const [id, text] of Object.entries(labels)) {
    const el = typeof doc.getElementById === 'function' ? doc.getElementById(id) : null
    if (el && text && el.textContent !== text) el.textContent = text
  }
}
