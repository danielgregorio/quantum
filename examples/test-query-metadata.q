<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-metadata" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: Enhanced query metadata (affectedRows, lastInsertId)
    Expected: UPDATE/DELETE return affectedRows, INSERT returns lastInsertId
    -->

    <!-- Test 1: INSERT with lastInsertId -->
    <q:set name="testUserName" value="Metadata Test User" type="string" />
    <q:set name="testUserEmail" value="metadata@test.com" type="string" />

    <q:query name="insertUser" datasource="test-sqlite">
        INSERT INTO users (name, email, password_hash, status, created_at)
        VALUES (:name, :email, 'hashed_pass', 'pending', datetime('now'))
        RETURNING id

        <q:param name="name" value="{testUserName}" type="string" />
        <q:param name="email" value="{testUserEmail}" type="string" />
    </q:query>

    <!-- Test 2: UPDATE with affectedRows -->
    <q:query name="activateUser" datasource="test-sqlite">
        UPDATE users
        SET status = 'active', updated_at = datetime('now')
        WHERE email = :email

        <q:param name="email" value="{testUserEmail}" type="string" />
    </q:query>

    <!-- Test 3: DELETE with affectedRows -->
    <q:query name="deleteUser" datasource="test-sqlite">
        DELETE FROM users WHERE email = :email

        <q:param name="email" value="{testUserEmail}" type="string" />
    </q:query>

    <!-- Return metadata summary -->
    <q:return value="Inserted ID: {insertUser.id}, Updated: {activateUser_result.affectedRows} rows, Deleted: {deleteUser_result.affectedRows} rows" />
</q:component>
