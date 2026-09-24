<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-of-queries" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: Query of Queries - In-memory SQL on previous query results
    Expected: Can run SQL queries on result sets without hitting database
    -->

    <!-- Step 1: Get all users from database -->
    <q:query name="allUsers" datasource="test-sqlite">
        SELECT id, name, email, status, created_at
        FROM users
    </q:query>

    <!-- Step 2: Filter results using Query of Queries (in-memory SQL) -->
    <q:query name="activeUsers" source="allUsers">
        SELECT name, email
        FROM allUsers
        WHERE status = 'active'
        ORDER BY name ASC
    </q:query>

    <!-- Step 3: Get count using Query of Queries -->
    <q:query name="activeCount" source="allUsers">
        SELECT COUNT(*) as total, status
        FROM allUsers
        WHERE status = 'active'
        GROUP BY status
    </q:query>

    <!-- Return summary -->
    <q:return value="Found {activeCount.total} active users out of {allUsers_result.recordCount} total users (Query of Queries in {activeUsers_result.executionTime}ms)" />
</q:component>
