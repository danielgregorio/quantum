<!-- The tasks app: `quantum test` in projects/tasks.
     Each q:test starts from a fresh database built by migrations/ (three tasks). -->

<q:test name="the list shows the summary and the tasks" page="/">
  <test:visit />
  <test:expect text="Total: 3" />
  <test:expect text="Open: 2" />
  <test:expect text="Done: 1" />
  <test:expect text="Write the first page" />
</q:test>

<q:test name="create a task" page="/">
  <test:submit action="create" title="Test the UI" priority="high" />
  <test:expect status="302" redirect="/" flash="Created: Test the UI" />
  <test:expect table="tasks" count="1" where="title = 'Test the UI' AND priority = 'high'" />
  <test:expect text="Total: 4" />
</q:test>

<q:test name="a title that is too short is refused on its field" page="/">
  <test:submit action="create" title="x" />
  <test:expect redirect="/" />
  <test:expect error="title" />
  <test:expect text="at least 3 characters" />
  <test:expect table="tasks" count="3" />
</q:test>

<q:test name="a priority outside the list is refused" page="/">
  <test:submit action="create" title="With a wrong priority" priority="urgent" />
  <test:expect error="priority" />
  <test:expect table="tasks" count="0" where="title = 'With a wrong priority'" />
</q:test>

<q:test name="finish a task and show the open ones" page="/">
  <test:given table="tasks" title="Buy bread" />
  <test:expect table="tasks" count="1" where="title = 'Buy bread' AND done = 0" />
  <test:submit action="toggle" id="4" show="open" />
  <test:expect redirect="/?show=open" />
  <test:expect table="tasks" count="1" where="id = 4 AND done = 1" />
  <test:expect no-text="Buy bread" />
  <test:expect text="Read the Quantum guide" />
</q:test>

<q:test name="delete a task" page="/">
  <test:submit action="delete" id="2" />
  <test:expect redirect="/" flash="Task deleted." />
  <test:expect table="tasks" count="0" where="id = 2" />
  <test:expect text="Total: 2" />
</q:test>

<q:test name="the page runs a fixed number of queries" page="/">
  <test:given table="tasks" />
  <test:given table="tasks" />
  <test:visit />
  <!-- two queries (the summary and the list), however many tasks there are -->
  <test:expect queries="2" />
  <test:expect var="show" value="all" />
</q:test>

<q:test name="the filter comes from the query string" page="/">
  <test:visit show="done" />
  <test:expect var="show" value="done" />
  <test:expect text="Install Quantum" />
  <test:expect no-text="Read the Quantum guide" />
</q:test>
