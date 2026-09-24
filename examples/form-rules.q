<q:component name="Cadastro">
  <!-- M1 (SPEC UI-9): the form takes each field's rules from the q:action it
       posts to. Open the page source: nome has required minlength="3",
       idade has type="number" min="18". When the server refuses a field, the
       page comes back with the values sent and each error next to its field.
       Serve it from an app's components/ with `quantum start`. -->

  <q:action name="cadastrar" method="POST">
    <q:param name="nome" required="true" minlength="3" maxlength="60" />
    <q:param name="idade" type="integer" min="18" max="120" />
    <q:param name="plano" enum="gratis,pro" default="gratis" />
    <q:param name="avisos" default="off" />
    <q:redirect url="/form-rules" flash="Cadastrado: {nome} ({plano}, avisos {avisos})" />
  </q:action>

  <ui:window title="Cadastro">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="cadastrar">
      <ui:formitem label="Nome"><ui:input bind="nome" /></ui:formitem>
      <ui:formitem label="Idade"><ui:input bind="idade" /></ui:formitem>
      <ui:formitem label="Plano"><ui:select bind="plano" /></ui:formitem>
      <ui:checkbox bind="avisos" label="Receber avisos" />
      <ui:button variant="primary">Cadastrar</ui:button>
    </ui:form>
  </ui:window>
</q:component>
