<!-- Next to the page it tests: the sheet (UI-13) and the edit form (UI-10).
     Neither page writes an action's rules: they come from the schema. -->

<q:test name="a cell edit is saved and recorded in the history" page="/planilha">
  <test:submit action="__edit" __table="tarefas" __key="1" __column="prioridade" value="baixa" />
  <test:expect redirect="/planilha" flash="Saved: prioridade" />
  <test:expect table="tarefas" count="1" where="id = 1 AND prioridade = 'baixa'" />
  <test:expect history="tarefas" count="1" op="update" where="id = 1" />
</q:test>

<q:test name="a cell refuses a value the schema does not allow" page="/planilha">
  <test:submit action="__edit" __table="tarefas" __key="1" __column="prioridade" value="urgente" />
  <test:expect table="tarefas" count="1" where="id = 1 AND prioridade = 'alta'" />
  <test:expect history="tarefas" count="0" />
</q:test>

<q:test name="the edit form validates with the schema's rules" page="/tarefa/1">
  <test:submit action="salvar" titulo="" prioridade="urgente" />
  <test:expect error="titulo" message="Required" />
  <test:expect error="prioridade" message="Must be one of: baixa, media, alta" />
  <test:expect table="tarefas" count="1" where="id = 1 AND titulo = 'Ler o guia do Quantum'" />
</q:test>

<q:test name="an edit is saved and shows in the task's history" page="/tarefa/1">
  <test:as user="ana" />
  <test:submit action="salvar" titulo="Ler o guia inteiro" prioridade="baixa" />
  <test:expect redirect="/" flash="Salva: Ler o guia inteiro" />
  <test:expect table="tarefas" count="1" where="id = 1 AND titulo = 'Ler o guia inteiro' AND prioridade = 'baixa'" />
  <test:expect history="tarefas" action="salvar" op="update" user="ana" where="id = 1" count="1" />
  <test:visit path="/tarefa/1" />
  <test:expect text="titulo: Ler o guia do Quantum → Ler o guia inteiro" />
</q:test>

<q:test name="a task that does not exist" page="/tarefa/99">
  <test:visit />
  <test:expect text="Essa tarefa não existe" />
</q:test>
