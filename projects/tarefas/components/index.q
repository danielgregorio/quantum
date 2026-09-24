<q:component name="Tarefas">
  <!-- Um app em ui:*: layout, formulário e lista vêm do UI Engine; a lógica é
       a da página — consultas, actions e as regras da SPEC. -->

  <q:action name="criar" method="POST">
    <q:param name="titulo" required="true" minlength="3" maxlength="200" />
    <q:param name="prioridade" default="media" enum="baixa,media,alta" />
    <q:query name="nova" datasource="db">
      INSERT INTO tarefas (titulo, prioridade) VALUES (:titulo, :prioridade)
      <q:param name="titulo" value="{titulo}" type="string" />
      <q:param name="prioridade" value="{prioridade}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Criada: {titulo}" />
  </q:action>

  <q:action name="alternar" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="filtro" default="todas" enum="todas,abertas,feitas" />
    <q:query name="troca" datasource="db">
      UPDATE tarefas SET feita = 1 - feita WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?filtro={filtro}" />
  </q:action>

  <q:action name="apagar" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="fora" datasource="db">
      DELETE FROM tarefas WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Tarefa apagada." />
  </q:action>

  <q:set name="filtro" value="{query.filtro}" default="todas" />

  <q:query name="contagem" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(feita = 0), 0) AS abertas, COALESCE(SUM(feita), 0) AS feitas
    FROM tarefas
  </q:query>

  <q:query name="tarefas" datasource="db">
    SELECT id, titulo, prioridade, feita FROM tarefas
    WHERE :filtro = 'todas' OR (:filtro = 'abertas' AND feita = 0) OR (:filtro = 'feitas' AND feita = 1)
    ORDER BY feita, CASE prioridade WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, id DESC
    <q:param name="filtro" value="{filtro}" type="string" />
  </q:query>

  <ui:window title="Tarefas">
    <!-- Lado a lado na tela larga; empilhado abaixo de 768 px (UI-2). -->
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="principal">

      <ui:vbox width="260" gap="md" id="lateral">
        <ui:panel title="Resumo">
          <ui:vbox gap="sm">
            <ui:text>Total: {contagem.total}</ui:text>
            <ui:text>Abertas: {contagem.abertas}</ui:text>
            <ui:text>Feitas: {contagem.feitas}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Mostrar">
          <ui:vbox gap="sm">
            <ui:link to="/?filtro=todas">Todas</ui:link>
            <ui:link to="/?filtro=abertas">Abertas</ui:link>
            <ui:link to="/?filtro=feitas">Feitas</ui:link>
            <ui:link to="/planilha">Planilha</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="conteudo">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="criar">
          <ui:hbox gap="sm">
            <ui:input bind="titulo" placeholder="O que precisa ser feito?" required="true" grow="true" />
            <ui:select bind="prioridade" options="media,alta,baixa" />
            <ui:button variant="primary">Criar</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tarefas">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tarefas.prioridade}</ui:badge>
            <ui:text>{tarefas.titulo}</ui:text>
            <ui:link to="/tarefa/{tarefas.id}">Editar</ui:link>
            <ui:button on-click="alternar" with="id={tarefas.id}, filtro={filtro}">{'Reabrir' if tarefas.feita else 'Concluir'}</ui:button>
            <ui:button on-click="apagar" with="id={tarefas.id}" variant="danger">Apagar</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tarefas_result.recordCount == 0">
          <ui:text>Nenhuma tarefa aqui.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
