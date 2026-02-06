<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: POST request with JSON body
Tests: Creating resources via POST
-->
<q:component xmlns:q="https://quantum.lang/ns" name="fetch-post-json">
    <q:set name="newUser" value="{name: 'John', email: 'john@example.com'}" />

    <q:fetch name="createdUser"
             url="/api/users"
             method="POST"
             body="{newUser}"
             onSuccess="handleUserCreated"
             onError="handleError">
        <q:loading>Creating user...</q:loading>
        <q:error>Failed to create user: {error}</q:error>
        <q:success>
            <div class="success-message">
                User created successfully!
                <p>ID: {createdUser.id}</p>
                <p>Name: {createdUser.name}</p>
            </div>
        </q:success>
    </q:fetch>
</q:component>
