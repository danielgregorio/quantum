<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Fetch with loading/error/success states
Tests: Full declarative state management
-->
<q:component xmlns:q="https://quantum.lang/ns" name="fetch-loading-states">
    <q:fetch name="users" url="/api/users" method="GET" cache="5m">
        <q:loading>
            <div class="skeleton-list">
                <div class="skeleton-item"></div>
                <div class="skeleton-item"></div>
                <div class="skeleton-item"></div>
            </div>
        </q:loading>
        <q:error>
            <div class="alert alert-danger">
                <strong>Error:</strong> {error}
                <button onclick="__qFetchRefetch('qfetch-1')">Retry</button>
            </div>
        </q:error>
        <q:success>
            <ul class="user-list">
                <q:loop var="user" items="{users}">
                    <li>{user.name} - {user.email}</li>
                </q:loop>
            </ul>
        </q:success>
    </q:fetch>
</q:component>
