---
order: 1
title: A first page, and a second
description: "Each file in components/ is a page at its own URL; a URL with no file is 404."
---

# A first page, and a second

**Task:** serve two pages that link to each other.

<<< @/../examples/cookbook/basics/first-page/quantum.config.yaml{yaml}

A file in `components/` is a page, at the URL of its path:
`components/index.q` answers `/` and `components/about.q` answers `/about`.
Start the server with `quantum start` in the folder that has
`quantum.config.yaml`.

<<< @/../examples/cookbook/basics/first-page/components/index.q{xml}

<<< @/../examples/cookbook/basics/first-page/components/about.q{xml}

A URL with no file answers `404`:

<<< @/../examples/cookbook/basics/first-page/tests/pages.test.q{xml}

<<< @/../examples/cookbook/basics/first-page/output/test-report.txt{text}

See [ROUTE-1](../../reference/spec.md#ROUTE-1).
