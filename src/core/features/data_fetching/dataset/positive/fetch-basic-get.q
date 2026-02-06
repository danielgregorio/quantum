<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Basic GET request
Tests: Simple data fetching without states
-->
<q:component xmlns:q="https://quantum.lang/ns" name="fetch-basic-get">
    <q:fetch name="users" url="https://api.example.com/users" method="GET" />

    <div>
        <h1>Users</h1>
        <p>Total: {users.length}</p>
    </div>
</q:component>
