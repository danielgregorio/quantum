<q:component name="Inbox">
  <ui:window title="Inbox">
    <!-- Side by side from md up; below md (768 px) the boxes stack. -->
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">
      <ui:vbox width="220" gap="sm" id="side">
        <ui:link to="/">Inbox (3)</ui:link>
        <ui:link to="/sent">Sent</ui:link>
        <!-- Only on wide screens: hidden below lg. -->
        <ui:text hide-below="lg">Tip: press / to search.</ui:text>
      </ui:vbox>

      <!-- grow takes the width the side box leaves. -->
      <ui:vbox gap="sm" grow="true">
        <ui:panel title="Welcome">
          <ui:text>The main content takes the rest of the width.</ui:text>
        </ui:panel>
        <ui:hbox gap="sm" justify="end">
          <ui:button>Archive</ui:button>
          <ui:button variant="primary">Reply</ui:button>
        </ui:hbox>
      </ui:vbox>
    </ui:hbox>
  </ui:window>
</q:component>
