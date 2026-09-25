// node docs/.vitepress/search-tokenize.check.mjs — exits 1 if the site's search
// cannot find a Chinese word inside a sentence (run by tests/docs/test_site.py).
//
// The default MiniSearch split keeps a Chinese sentence as one "word" (there are
// no spaces), so a search for a word in the middle of it finds nothing. The
// site's tokenizer (Intl.Segmenter) splits it into words.

import MiniSearch from 'minisearch'
import { tokenize } from './search-tokenize.js'

const pages = [
  { id: 'zh', text: '文档目前为英文，中文翻译正在进行中。' },
  { id: 'en', text: 'Pagination with q:query paginate and ui:pager' },
]

function search(options, query) {
  const index = new MiniSearch({ fields: ['text'], ...options })
  index.addAll(pages)
  return index.search(query, { prefix: true, ...(options.tokenize ? { tokenize: options.tokenize } : {}) })
    .map(r => r.id)
}

const failures = []
for (const query of ['翻译', '进行']) {        // words in the middle of the sentence
  if (search({}, query).includes('zh')) failures.push(`the default split found ${query}: this check proves nothing`)
  if (!search({ tokenize }, query).includes('zh')) failures.push(`the site's tokenizer did not find ${query}`)
}
for (const query of ['pagination', 'paginate', 'pager', 'query']) {   // 'pager' is inside ui:pager
  if (!search({ tokenize }, query).includes('en')) failures.push(`the site's tokenizer did not find ${query}`)
}
if (failures.length) {
  console.error(failures.join('\n'))
  process.exit(1)
}
console.log('ok: Chinese words inside a sentence are found; English still is')
