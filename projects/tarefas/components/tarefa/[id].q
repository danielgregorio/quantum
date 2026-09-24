<q:component name="EditarTarefa">
  <!-- Formulário a partir da tabela (M17, SPEC UI-10): a action toma as
       regras de `titulo` e `prioridade` do esquema de `tarefas` (NOT NULL,
       CHECK … IN) e o formulário, sem campos próprios, desenha um campo por
       coluna, aberto com os valores da tarefa. -->

  <q:action name="salvar" method="POST" table="tarefas" datasource="db" columns="titulo,prioridade">
    <q:query name="alterada" datasource="db">
      UPDATE tarefas SET titulo = :titulo, prioridade = :prioridade WHERE id = :id
      <q:param name="titulo" value="{titulo}" type="string" />
      <q:param name="prioridade" value="{prioridade}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Salva: {titulo}" />
  </q:action>

  <q:query name="tarefa" datasource="db">
    SELECT id, titulo, prioridade FROM tarefas WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Editar tarefa">
    <ui:vbox gap="md" padding="lg">
      <ui:link to="/">Voltar</ui:link>
      <q:if condition="tarefa_result.recordCount == 0">
        <ui:alert variant="danger">Essa tarefa não existe.</ui:alert>
      </q:if>
      <q:else>
        <ui:form on-submit="salvar" values="{tarefa}" submit="Salvar" />
        <ui:section title="Histórico">
          <ui:history table="tarefas" key="{id}" datasource="db" />
        </ui:section>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
