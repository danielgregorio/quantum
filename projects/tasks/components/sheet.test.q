<!-- Next to the page it tests: the sheet (UI-13) and the edit form (UI-10).
     Neither page writes an action's rules: they come from the schema. -->

<q:test name="a cell edit is saved and recorded in the history" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="low" />
  <test:expect redirect="/sheet" flash="Saved: priority" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'low'" />
  <test:expect history="tasks" count="1" op="update" where="id = 1" />
</q:test>

<q:test name="a cell refuses a value the schema does not allow" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="urgent" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'high'" />
  <test:expect history="tasks" count="0" />
</q:test>

<q:test name="the edit form validates with the schema's rules" page="/task/1">
  <test:submit action="save" title="" priority="urgent" />
  <test:expect error="title" message="Required" />
  <test:expect error="priority" message="Must be one of: low, medium, high" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the Quantum guide'" />
</q:test>

<q:test name="an edit is saved and shows in the task's history" page="/task/1">
  <test:as user="ana" />
  <test:submit action="save" title="Read the whole guide" priority="low" />
  <test:expect redirect="/" flash="Saved: Read the whole guide" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the whole guide' AND priority = 'low'" />
  <test:expect history="tasks" action="save" op="update" user="ana" where="id = 1" count="1" />
  <test:visit path="/task/1" />
  <test:expect text="title: Read the Quantum guide → Read the whole guide" />
</q:test>

<q:test name="a task that does not exist" page="/task/99">
  <test:visit />
  <test:expect text="That task does not exist" />
</q:test>
