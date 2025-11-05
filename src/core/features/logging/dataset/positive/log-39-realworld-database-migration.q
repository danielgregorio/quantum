<!-- Positive: Real-world database migration logging -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldDBMigration" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="migration" value='{"version": "2.1.0", "tables": 15, "records": 125000, "status": "in_progress"}' operation="json" />

  <q:log level="info"
         message="Database migration {migration.version} started"
         context="{migration}" />

  <q:log level="info"
         message="Migrated {migration.records} records across {migration.tables} tables" />

  <q:return value="Migration logged" />
</q:component>
