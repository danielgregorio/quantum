<q:component name="Done">
  <ui:window title="All clear">
    <q:if condition="flash">
      <ui:alert variant="{flashType}">{flash}</ui:alert>
    </q:if>
    <ui:link to="/">Back to the notes</ui:link>
  </ui:window>
</q:component>
