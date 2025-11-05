<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-loop" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: Using query results in loops with clean syntax
    Expected: Query results can be iterated using query loop shorthand
    -->

    <!-- Fetch users -->
    <q:query name="activeUsers" datasource="test-sqlite">
        SELECT id, name, email, created_at
        FROM users
        WHERE status = :status
        ORDER BY name ASC

        <q:param name="status" value="active" type="string" />
    </q:query>

    <!-- Process results using query loop shorthand -->
    <q:set name="userCount" value="0" type="integer" />
    <q:set name="emailList" value="" type="string" />

    <q:loop query="activeUsers" index="idx">
        <!-- Increment counter -->
        <q:set name="userCount" operation="increment" step="1" />

        <!-- Build comma-separated email list -->
        <q:if condition="{idx} > 0">
            <q:set name="emailList" value="{emailList}, {activeUsers.email}" />
        <q:else>
            <q:set name="emailList" value="{activeUsers.email}" />
        </q:else>
        </q:if>

        <!-- Return each user (loop returns collect into array) -->
        <q:return value="{idx + 1}. {activeUsers.name} ({activeUsers.email})" />
    </q:loop>

    <!-- Return summary as final result -->
    <q:return value="Processed {userCount} users. Emails: {emailList}" />
</q:component>
