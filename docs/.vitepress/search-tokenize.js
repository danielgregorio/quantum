// Word splitting for the local search, shared by the index build (config.js)
// and the browser (theme/index.js), so a query is split like the pages were.
//
// MiniSearch splits on spaces and punctuation by default. Chinese has no
// spaces: a whole sentence became one "word", and a search for a word inside
// it found nothing. Intl.Segmenter splits by words in every language the
// runtime knows (Chinese included) and keeps Latin words as they are. Where it
// does not exist (very old browsers), the default split is used.

const SPACE_OR_PUNCTUATION = /[\n\r\p{Z}\p{P}]+/u

const segmenter = typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function'
  ? new Intl.Segmenter('zh', { granularity: 'word' })
  : null

export function tokenize(text) {
  if (!segmenter) return String(text).split(SPACE_OR_PUNCTUATION).filter(Boolean)
  const words = []
  for (const part of segmenter.segment(String(text))) {
    if (!part.isWordLike) continue
    // The segmenter keeps "q:loop" and "ui:pager" as one word (":" joins
    // letters in Unicode's rules); the default split made them two, so a
    // search for "loop" found q:loop. Split them the same way.
    for (const word of part.segment.split(SPACE_OR_PUNCTUATION)) {
      if (word) words.push(word)
    }
  }
  return words
}
