---
order: 3
title: Search as you type
description: "A field that refreshes the results after each pause in typing — the page's own query does the search."
---

# Search as you type

**Task:** a search field over books that updates the list while you type,
and still works without JavaScript.

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/migrations/V001_books.sql{sql}

The search is a GET parameter (`?q=`), read by the page's own query.
`search="results"` on the field asks for the same page after each pause in
typing and swaps only the element with `id="results"`; the URL follows, so
the result can be shared or reloaded.

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/components/index.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/tests/search.test.q{xml}

<<< @/../examples/cookbook/data-and-sql/search-as-you-type/output/test-report.txt{text}

See [UI-12](../../reference/spec.md#UI-12).
