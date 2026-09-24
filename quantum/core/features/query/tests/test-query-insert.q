<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-insert" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: INSERT query with RETURNING clause (PostgreSQL)
    Expected: Record inserted and ID accessible directly
    -->

    <!-- Set test data -->
    <q:set name="newUserName" value="John Doe" type="string" />
    <q:set name="newUserEmail" value="john.doe@example.com" type="string" />
    <q:set name="newUserPassword" value="hashed_password_here" type="string" />

    <q:query name="insertResult" datasource="test-postgres">
        INSERT INTO users (name, email, password_hash, status, created_at)
        VALUES (:name, :email, :password, 'active', NOW())
        RETURNING id, name, email, created_at

        <q:param name="name" value="{newUserName}" type="string" maxLength="100" />
        <q:param name="email" value="{newUserEmail}" type="string" maxLength="255" />
        <q:param name="password" value="{newUserPassword}" type="string" />
    </q:query>

    <!-- Access fields directly (single-row result) -->
    <q:return value="User '{insertResult.name}' created with ID {insertResult.id} in {insertResult_result.executionTime}ms" />
</q:component>
