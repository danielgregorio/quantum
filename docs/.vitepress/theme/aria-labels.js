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

// The same labels in the HTML the build writes (config.js transformHtml), so a
// screen reader hears the page's language before any script runs: the text of
// the element with each id is replaced. An id that is not in the page is skipped.
export function ariaLabelsInHtml(html, labels) {
  if (!html || !labels) return html
  let out = html
  for (const [id, text] of Object.entries(labels)) {
    if (!text) continue
    const element = new RegExp('(<(\\w+)\\b[^>]*\\bid="' + id + '"[^>]*>)[^<]*(</\\2>)')
    out = out.replace(element, (_, open, _tag, close) => open + escapeHtml(text) + close)
  }
  return out
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
