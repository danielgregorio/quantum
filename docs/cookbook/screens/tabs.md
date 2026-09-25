---
order: 3
title: Tabs
description: "ui:tabpanel with one ui:tab per section of a page."
---

# Tabs

**Task:** split a page into sections, one visible at a time.

<<< @/../examples/cookbook/screens/tabs/quantum.config.yaml{yaml}

Each `ui:tab` is a section with a `title`; the first one opens with the
page. The content of every tab is on the page, so a hidden tab is still
there for search and for tests.

<<< @/../examples/cookbook/screens/tabs/components/index.q{xml}

<<< @/../examples/cookbook/screens/tabs/tests/tabs.test.q{xml}

<<< @/../examples/cookbook/screens/tabs/output/test-report.txt{text}

`ui:tabpanel` is in the Core set drawn by the browser, the console and the
desktop window: [UI-7](../../reference/spec.md#UI-7).
