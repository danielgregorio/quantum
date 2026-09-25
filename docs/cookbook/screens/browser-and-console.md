---
order: 6
title: The same page in a terminal
description: "One ui:* page, served to the browser by quantum start and drawn in a terminal by quantum console."
---

# The same page in a terminal

**Task:** use the same page from a browser and from a terminal.

<<< @/../examples/cookbook/screens/browser-and-console/quantum.config.yaml{yaml}

A page made of Core `ui:*` tags is not tied to HTML. `quantum start`
serves it to a browser; `quantum console` draws it in the terminal, and
`quantum desktop` in a local window. The console asks the same server for
the page's view tree and posts the same actions: the rule on `name`, the
flash and the session work the same way, with nothing translated.

<<< @/../examples/cookbook/screens/browser-and-console/components/index.q{xml}

In the browser, `quantum test`:

<<< @/../examples/cookbook/screens/browser-and-console/tests/guests.test.q{xml}

<<< @/../examples/cookbook/screens/browser-and-console/output/test-report.txt{text}

In the console,
[`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py) opens the same app
in the console renderer. It checks that every text this suite expects on a
plain visit is on the console screen, then types a name that is too short
and one that is fine, and presses **Sign**: the console shows the field's
error, then the flash and the new name.

```bash
quantum start      # http://localhost:8080
quantum console    # the same page in this terminal
```

See [UI-3](../../reference/spec.md#UI-3) and [UI-7](../../reference/spec.md#UI-7).
