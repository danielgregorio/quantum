---
order: 4
title: Cards
description: "ui:card with a header, a body and a footer, in a ui:grid; or a card with just a title."
---

# Cards

**Task:** show a few items side by side, each in its own box.

<<< @/../examples/cookbook/screens/cards/quantum.config.yaml{yaml}

`ui:card` holds a `ui:card-header`, a `ui:card-body` and a
`ui:card-footer`, each optional. `ui:grid columns="3"` lays the cards out
in three columns. A card with only a title and some text needs no parts:
`title=` is enough.

<<< @/../examples/cookbook/screens/cards/components/index.q{xml}

<<< @/../examples/cookbook/screens/cards/tests/cards.test.q{xml}

<<< @/../examples/cookbook/screens/cards/output/test-report.txt{text}

See [UI-7](../../reference/spec.md#UI-7).
