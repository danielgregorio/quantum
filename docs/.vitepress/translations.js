// Translated pages and the English page each one came from.
//
// A translated page (docs/pt/..., docs/es/..., docs/zh/...) names its English
// source in its frontmatter, with the hash of the English text it was
// translated from:
//
//   source: guide/installation.md
//   source_hash: 3f2a9c1b7d4e
//
// At build time the English file is hashed again. When the hash differs, the
// English changed after the translation, and the page shows a notice that it
// may be out of date (TranslationNotice.vue). scripts/translation-status.py
// reports those pages and stamps a page again once it is updated; it computes
// the same hash: sha256 of the text with CRLF as LF, first 12 hex digits.

import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

export function sourceHash(text) {
  return crypto.createHash('sha256').update(text.replace(/\r\n/g, '\n'), 'utf8').digest('hex').slice(0, 12)
}

// For VitePress transformPageData: marks a translation whose English moved on.
export function markStaleTranslation(pageData, docsDir) {
  const { source, source_hash: stamped } = pageData.frontmatter || {}
  if (!source) return
  const english = path.join(docsDir, source)
  if (!fs.existsSync(english)) return   // tests/docs/test_translations.py fails on this
  const current = sourceHash(fs.readFileSync(english, 'utf8'))
  if (current !== stamped) {
    pageData.frontmatter.translationStale = true
  }
  pageData.frontmatter.englishLink = '/' + source.replace(/(^|\/)index\.md$/, '$1').replace(/\.md$/, '')
}

// `node docs/.vitepress/translations.js <file>` prints the hash (the tests
// check that Python and this module agree).
if (process.argv[1] && process.argv[1].endsWith('translations.js') && process.argv[2]) {
  console.log(sourceHash(fs.readFileSync(process.argv[2], 'utf8')))
}
