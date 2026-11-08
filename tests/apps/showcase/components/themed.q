<q:component name="Themed">
  <!-- UI-21: a page's ui:theme gives its colours to the browser, the console and the TUI
       (the Hive's screen keeps its palette): tests/apps/test_ui_parity_script.py, test_a_page_s_theme_*. -->
  <ui:theme preset="dark">
    <ui:color name="primary" value="#ff00aa" />
  </ui:theme>
  <ui:window title="Themed">
    <ui:button variant="primary">Go</ui:button>
  </ui:window>
</q:component>
