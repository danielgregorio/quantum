<q:component name="Planilha">
  <!-- Tabela que ordena e se edita (M16, SPEC UI-13): os cabeçalhos ordenam
       no SQL (sortable), e cada célula é um formulário que grava uma coluna
       de uma linha, validada pelas regras do esquema — sem action escrita. -->

  <q:query name="tarefas" datasource="db" sortable="true" paginate="true" page_size="20">
    SELECT id, titulo, prioridade, feita FROM tarefas ORDER BY id
  </q:query>

  <ui:window title="Planilha de tarefas">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:link to="/">Voltar</ui:link>
        <ui:text>Clique num cabeçalho para ordenar; edite a célula e confirme com ✓ (ou Enter).</ui:text>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <ui:table source="{tarefas}" sort="true" edit="tarefas" datasource="db">
        <ui:column key="titulo" label="Título" />
        <ui:column key="prioridade" label="Prioridade" />
        <ui:column key="feita" label="Feita" />
      </ui:table>
      <ui:pager for="tarefas" />
    </ui:vbox>
  </ui:window>
</q:component>
