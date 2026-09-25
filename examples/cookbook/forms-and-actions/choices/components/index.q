<q:component name="Coffee">
  <q:action name="order" method="POST">
    <!-- enum is the list: the form's select and radios take their options
         from it (UI-9), and the server refuses anything else (ACT-2). -->
    <q:param name="size" required="true" enum="small,medium,large" />
    <q:param name="milk" enum="none,whole,oat" default="none" />
    <q:param name="to_go" type="boolean" default="false" />
    <q:query name="placed" datasource="db">
      INSERT INTO orders (size, milk, to_go) VALUES (:size, :milk, :to_go)
      <q:param name="size" value="{size}" type="string" />
      <q:param name="milk" value="{milk}" type="string" />
      <q:param name="to_go" value="{to_go}" type="boolean" />
    </q:query>
    <q:redirect url="/" flash="A {size} coffee, milk: {milk}{', to go' if to_go else ''}." />
  </q:action>

  <ui:window title="Order a coffee">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="order" submit="Order">
      <ui:formitem label="Size"><ui:select bind="size" /></ui:formitem>
      <ui:formitem label="Milk"><ui:radio bind="milk" /></ui:formitem>
      <ui:checkbox bind="to_go" label="To go" />
    </ui:form>
  </ui:window>
</q:component>
