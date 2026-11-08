# UI parity: every `ui:*` tag in every renderer

<!-- Written by `python -m quantum.runtime.ui_parity > UI_PARITY.md` from quantum/runtime/ui_parity.py;
     tests/conformance/test_ui_parity_map.py fails when they differ, or when a renderer does not do
     what the table says. -->

What each renderer of a page does with each tag (SPEC.md UI-7, UI-21): ✓ drawn, with what is worth
saying about the form it takes; "— says so" not drawn yet, and the renderer says
`[ui:kind is not drawn ...]` in its place, never something else (UI-7). The desktop is the browser in
a window of its own (UI-4). A tag enters the Core set when every renderer draws it.

| Tag | Tier | Browser | Console | Hive's screen | TUI |
|---|---|---|---|---|---|
| `ui:accordion` | Experimental | ✓ drawn, its sections always open | — says so | — says so | — says so |
| `ui:alert` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:animate` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:avatar` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:badge` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:breadcrumb` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:breadcrumb-item` (part of `ui:breadcrumb`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:button` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:calendar` | Experimental | ✓ the month; it does not move or pick | — says so | — says so | — says so |
| `ui:card` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:card-body` (part of `ui:card`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:card-footer` (part of `ui:card`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:card-header` (part of `ui:card`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:carousel` | Experimental | ✓ the first slide; the arrows do nothing | — says so | — says so | — says so |
| `ui:chart` | Core | ✓ | ✓ bars of characters | ✓ bars | ✓ bars of characters |
| `ui:checkbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:color` (part of `ui:theme`) | Experimental | standalone only | standalone only | standalone only | standalone only |
| `ui:column` (part of `ui:table`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:date-picker` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:dividedbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:dropdown` | Experimental | ✓ | — says so | — says so | — says so |
| `ui:footer` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:form` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:formitem` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:grid` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:hbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:header` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:history` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:image` | Core | ✓ | ✓ [its alt] | ✓ [its alt] | ✓ |
| `ui:input` | Core | ✓ | ✓ a file field says to attach from the browser (UI-14) | ✓ | ✓ |
| `ui:item` (part of `ui:list`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:link` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:list` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:loading` | Core | ✓ | ✓ | ✓ a still mark | ✓ |
| `ui:log` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:markdown` | Core | ✓ | ✓ | ✓ its emphasis as plain text (the font has one face) | ✓ |
| `ui:menu` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:modal` | Experimental | ✓ drawn when `open`; nothing opens it | — says so | — says so | — says so |
| `ui:option` (part of `ui:select`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:pager` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:pagination` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:panel` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:progress` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:radio` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:rule` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:scrollbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:section` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:select` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:skeleton` | Core | ✓ | ✓ shaded lines | ✓ | ✓ shaded lines |
| `ui:slide` (part of `ui:carousel`) | Experimental | ✓ the first slide; the arrows do nothing | — says so | — says so | — says so |
| `ui:spacer` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:step` (part of `ui:stepper`) | Experimental | ✓ the current step; the steps do not move | — says so | — says so | — says so |
| `ui:stepper` | Experimental | ✓ the current step; the steps do not move | — says so | — says so | — says so |
| `ui:stream` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:switch` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:tab` (part of `ui:tabpanel`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:table` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:tabpanel` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:text` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:theme` | Experimental | standalone only | standalone only | standalone only | standalone only |
| `ui:toast` | Experimental | ✓ drawn; it does not go away | — says so | — says so | — says so |
| `ui:toast-container` | Experimental | ✓ an empty box | — says so | — says so | — says so |
| `ui:tooltip` | Experimental | ✓ | — says so | — says so | — says so |
| `ui:tree` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:validator` | Experimental | standalone only | standalone only | standalone only | standalone only |
| `ui:vbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:window` | Core | ✓ | ✓ | ✓ | ✓ |

## Not elements of a page

- `ui:validator`: a form's rules come from its action's q:params in a page (UI-9); it applies to a standalone `q:application type="ui"` build (UI-8).
- `ui:theme`: a page's look is the design tokens' (ui_html_templates.CSS_THEME); it applies to a standalone `q:application type="ui"` build (UI-8).
- `ui:color`: a page's look is the design tokens' (ui_html_templates.CSS_THEME); it applies to a standalone `q:application type="ui"` build (UI-8).

53 of 67 tags are drawn by every renderer.
