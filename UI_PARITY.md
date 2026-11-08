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
| `ui:accordion` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:alert` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:animate` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:avatar` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:badge` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:breadcrumb` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:breadcrumb-item` (part of `ui:breadcrumb`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:button` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:calendar` | Core | ✓ | ✓ | ✓ the days of the months around it left blank | ✓ the days of the months around it left blank |
| `ui:card` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:card-body` (part of `ui:card`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:card-footer` (part of `ui:card`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:card-header` (part of `ui:card`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:carousel` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:chart` | Core | ✓ | ✓ bars of characters | ✓ bars | ✓ bars of characters |
| `ui:checkbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:color` (part of `ui:theme`) | Core | ✓ its colours | ✓ its colours | ✓ the screen keeps its palette | ✓ its colours |
| `ui:column` (part of `ui:table`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:date-picker` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:dividedbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:dropdown` | Core | ✓ | ✓ | ✓ | ✓ |
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
| `ui:modal` | Core | ✓ | ✓ | ✓ | ✓ |
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
| `ui:slide` (part of `ui:carousel`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:spacer` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:step` (part of `ui:stepper`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:stepper` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:stream` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:switch` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:tab` (part of `ui:tabpanel`) | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:table` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:tabpanel` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:text` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:theme` | Core | ✓ its colours | ✓ its colours | ✓ the screen keeps its palette | ✓ its colours |
| `ui:toast` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:toast-container` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:tooltip` | Core | ✓ | ✓ | ✓ its tip on the status line while it has the focus | ✓ |
| `ui:tree` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:validator` | Core | ✓ checked by the server | ✓ checked by the server | ✓ checked by the server | ✓ checked by the server |
| `ui:vbox` | Core | ✓ | ✓ | ✓ | ✓ |
| `ui:window` | Core | ✓ | ✓ | ✓ | ✓ |

## Not elements of a page

- `ui:validator`: a rule of its form, checked by the server when the form is sent (the error comes back by its field, UI-9).
- `ui:theme`: the page's colours: the browser's CSS variables, the console's and the TUI's colours; the Hive's screen keeps its palette.
- `ui:color`: one of its ui:theme's colours.

67 of 67 tags are drawn by every renderer.
