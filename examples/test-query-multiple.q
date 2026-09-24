<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-multiple" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: Multiple queries in single component
    Expected: All queries execute and results are accessible
    -->

    <!-- Query 1: Get users -->
    <q:query name="users" datasource="test-sqlite">
        SELECT id, name, email FROM users
        WHERE status = 'active'
        LIMIT 5
    </q:query>

    <!-- Query 2: Get count -->
    <q:query name="userCount" datasource="test-sqlite">
        SELECT COUNT(*) as total FROM users WHERE status = 'active'
    </q:query>

    <!-- Query 3: Get recent activity -->
    <q:query name="recentActivity" datasource="test-sqlite">
        SELECT user_id, action, created_at
        FROM activity_log
        ORDER BY created_at DESC
        LIMIT 10
    </q:query>

    <!-- Display all results -->
    <q:return value="Found {userCount.total} active users, showing first {users_result.recordCount}" />
</q:component>
