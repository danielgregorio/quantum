<q:component name="More">
  <!-- UI-21: the tags beyond the layout set, on one page. The parity test's second script
       (tests/apps/test_ui_parity_script.py, MORE) runs on it in the browser, the console,
       the TUI and on the screen. -->

  <q:action name="pick" method="POST">
    <q:param name="value" required="true" />
    <q:redirect url="/more" flash="Picked: {value}" />
  </q:action>

  <q:action name="book" method="POST">
    <q:param name="day" type="date" required="true" />
    <q:redirect url="/more" flash="Booked: {day}" />
  </q:action>

  <q:set name="sales" type="array" value='[{"label": "Mon", "value": 3}, {"label": "Tue", "value": 6}]' />
  <q:set name="folders" type="array" value='[{"label": "Docs", "children": [{"label": "Guide", "value": "guide"}, {"label": "Reference", "value": "reference"}]}, {"label": "Archive", "value": "archive"}]' />
  <q:set name="events" type="array" value='["started", "listening on 8080"]' />

  <ui:window title="More">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>

    <ui:breadcrumb separator=">">
      <ui:breadcrumb-item label="Home" to="/" />
      <ui:breadcrumb-item label="Library" to="/more" />
      <ui:breadcrumb-item label="Shelf" />
    </ui:breadcrumb>

    <ui:menu>
      <ui:option value="new" on-click="pick">New file</ui:option>
      <ui:option value="open" on-click="pick">Open file</ui:option>
    </ui:menu>

    <ui:hbox gap="md">
      <ui:avatar name="Ana Lima" status="online" />
      <ui:text>Signed in as Ana Lima</ui:text>
    </ui:hbox>

    <ui:markdown>
      ## Notes

      Some **bold** words and `code`.

      - first point
      - second point
    </ui:markdown>

    <ui:hbox gap="md" stack-below="md">
      <ui:chart type="bar" title="Sales" source="{sales}" grow="true" />
      <ui:chart type="pie" title="Share" labels="Red,Blue" values="1,3" grow="true" />
    </ui:hbox>

    <ui:tree source="{folders}" on-select="pick" />

    <ui:log max-lines="2" source="{events}">booting</ui:log>

    <ui:dividedbox>
      <ui:text>Left pane</ui:text>
      <ui:text>Right pane</ui:text>
    </ui:dividedbox>

    <ui:pagination total="45" page-size="10" show-total="true" />

    <ui:skeleton variant="text" lines="2" />
    <ui:loading text="Fetching" />

    <ui:form on-submit="book">
      <ui:date-picker bind="day" />
      <ui:button>Book</ui:button>
    </ui:form>
  </ui:window>
</q:component>
