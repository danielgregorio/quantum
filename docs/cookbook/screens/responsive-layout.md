---
order: 1
title: A layout that fits the screen
description: "ui:hbox side by side on a wide screen, stacked on a narrow one, with grow, width and hide-below."
---

# A layout that fits the screen

**Task:** a side menu next to the content on a wide screen, above it on a phone.

<<< @/../examples/cookbook/screens/responsive-layout/quantum.config.yaml{yaml}

`stack-below="md"` puts the boxes of a `ui:hbox` one above the other below
the `md` width (768 px in the browser, 96 columns in a terminal). `width`
fixes the side box, `grow="true"` gives the content the rest, and
`hide-below="lg"` keeps a hint for wide screens only.

<<< @/../examples/cookbook/screens/responsive-layout/components/index.q{xml}

`quantum test` reads the page's text, not its layout, so it checks the
content:

<<< @/../examples/cookbook/screens/responsive-layout/tests/layout.test.q{xml}

<<< @/../examples/cookbook/screens/responsive-layout/output/test-report.txt{text}

The stacking itself is checked in the console, where a test can measure it:
at 80 columns `#main` is stacked, at 140 it is side by side and `#side` is
220 / 8 = 27 columns wide
([`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py)). The rule:
[UI-2](../../reference/spec.md#UI-2).
