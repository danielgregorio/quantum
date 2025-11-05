<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-basic" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: Basic SELECT query with query loop syntax
    Expected: Query executes successfully and uses clean loop syntax
    -->

    <q:query name="users" datasource="test-postgres">
        SELECT id, name, email, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 10
    </q:query>

    <!-- Display results using query loop shorthand -->
    <q:loop query="users">
        <q:return value="User: {users.name} ({users.email})" />
    </q:loop>

    <!-- Return summary as final component result -->
    <q:return value="Total users: {users_result.recordCount}, Time: {users_result.executionTime}ms" />
</q:component>
