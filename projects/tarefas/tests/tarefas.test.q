<!-- The tasks app, tested in its own language: `quantum test` in projects/tarefas.
     Each q:test starts from a fresh database built by migrations/ (three tasks).
     The app's content is Portuguese, so the expected texts are too. -->

<q:test name="the list shows the summary and the tasks" page="/">
  <test:visit />
  <test:expect text="Total: 3" />
  <test:expect text="Abertas: 2" />
  <test:expect text="Feitas: 1" />
  <!-- DB-8: the .sql is read as UTF-8 (on Windows it became "pÃ¡gina") -->
  <test:expect text="Escrever a primeira página" />
</q:test>

<q:test name="create a task" page="/">
  <test:submit action="criar" titulo="Testar a UI" prioridade="alta" />
  <test:expect status="302" redirect="/" flash="Criada: Testar a UI" />
  <test:expect table="tarefas" count="1" where="titulo = 'Testar a UI' AND prioridade = 'alta'" />
  <test:expect text="Total: 4" />
</q:test>

<q:test name="a title that is too short is refused on its field" page="/">
  <test:submit action="criar" titulo="x" />
  <test:expect redirect="/" />
  <test:expect error="titulo" />
  <test:expect text="at least 3 characters" />
  <test:expect table="tarefas" count="3" />
</q:test>

<q:test name="a priority outside the list is refused" page="/">
  <test:submit action="criar" titulo="Com prioridade errada" prioridade="urgente" />
  <test:expect error="prioridade" />
  <test:expect table="tarefas" count="0" where="titulo = 'Com prioridade errada'" />
</q:test>

<q:test name="finish a task and filter the open ones" page="/">
  <test:given table="tarefas" titulo="Comprar pão" />
  <test:expect table="tarefas" count="1" where="titulo = 'Comprar pão' AND feita = 0" />
  <test:submit action="alternar" id="4" filtro="abertas" />
  <test:expect redirect="/?filtro=abertas" />
  <test:expect table="tarefas" count="1" where="id = 4 AND feita = 1" />
  <test:expect no-text="Comprar pão" />
  <test:expect text="Ler o guia do Quantum" />
</q:test>

<q:test name="delete a task" page="/">
  <test:submit action="apagar" id="2" />
  <test:expect redirect="/" flash="Tarefa apagada." />
  <test:expect table="tarefas" count="0" where="id = 2" />
  <test:expect text="Total: 2" />
</q:test>

<q:test name="the page runs a fixed number of queries" page="/">
  <test:given table="tarefas" />
  <test:given table="tarefas" />
  <test:visit />
  <!-- two queries (the summary and the list), however many tasks there are -->
  <test:expect queries="2" />
  <test:expect var="filtro" value="todas" />
</q:test>

<q:test name="the filter comes from the query string" page="/">
  <test:visit filtro="feitas" />
  <test:expect var="filtro" value="feitas" />
  <test:expect text="Instalar o Quantum" />
  <test:expect no-text="Ler o guia do Quantum" />
</q:test>
