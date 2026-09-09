<!-- Variables and Databinding -->
<q:component name="Variables">
  <q:set name="title" value="Quantum Framework" />
  <q:set name="version" type="number" value="1" />
  <q:set name="description" value="A declarative web framework" />

  <div class="card">
    <h1>{title}</h1>
    <p>Version: {version}</p>
    <p>{description}</p>
  </div>
</q:component>
