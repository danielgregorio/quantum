// The pages each language has, for the language switcher (theme/langs.js): the
// routes TRANSLATED lists in locales.js, and, under a listed section index such
// as '/cookbook/' or '/blog/', the translated pages found in that folder. One
// source of truth: a page reaches the switcher only through TRANSLATED.
// tests/docs/test_language_switch.py checks that every route points to a page.
//
//   node docs/.vitepress/translated-paths.js   # the map, as JSON
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { TRANSLATED } from './locales.js'

const DOCS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function pagesUnder(dir, prefix) {
  const out = []
  if (!fs.existsSync(dir)) return out
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) out.push(...pagesUnder(path.join(dir, entry.name), `${prefix}${entry.name}/`))
    else if (entry.name.endsWith('.md')) {
      out.push(entry.name === 'index.md' ? prefix : prefix + entry.name.slice(0, -3))
    }
  }
  return out
}

export function translatedPaths(docs = DOCS) {
  const map = {}
  for (const [lang, routes] of Object.entries(TRANSLATED)) {
    const all = new Set(['/'])                        // the language's home
    for (const route of routes) {
      all.add(route)
      if (route.endsWith('/') && route !== '/') {
        for (const page of pagesUnder(path.join(docs, lang, route), route)) all.add(page)
      }
    }
    map[lang] = [...all].sort()
  }
  return map
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  console.log(JSON.stringify(translatedPaths(), null, 1))
}
