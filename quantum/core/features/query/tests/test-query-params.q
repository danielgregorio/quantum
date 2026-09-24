<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-params" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: SELECT query with parameter binding
    Expected: Parameters are validated and bound correctly, SQL injection prevented
    -->

    <!-- Set test parameters -->
    <q:set name="searchStatus" value="active" type="string" />
    <q:set name="resultLimit" value="5" type="integer" />

    <q:query name="filteredUsers" datasource="test-postgres">
        SELECT id, name, email, status, created_at
        FROM users
        WHERE status = :status
        ORDER BY created_at DESC
        LIMIT :limit

        <q:param name="status" value="{searchStatus}" type="string" />
        <q:param name="limit" value="{resultLimit}" type="integer" />
    </q:query>

    <!-- Display results using clean query loop syntax -->
    <q:loop query="filteredUsers">
        <q:return value="User: {filteredUsers.name} - Status: {filteredUsers.status}" />
    </q:loop>

    <!-- Final summary -->
    <q:return value="Found {filteredUsers_result.recordCount} users with status '{searchStatus}' in {filteredUsers_result.executionTime}ms" />
</q:component>
