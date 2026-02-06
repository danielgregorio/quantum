<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Fetch with caching
Tests: Response caching with TTL
-->
<q:component xmlns:q="https://quantum.lang/ns" name="fetch-with-cache">
    <!-- Cache for 5 minutes -->
    <q:fetch name="categories"
             url="/api/categories"
             method="GET"
             cache="5m"
             cacheKey="all-categories">
        <q:loading>Loading categories...</q:loading>
        <q:success>
            <select>
                <q:loop var="cat" items="{categories}">
                    <option value="{cat.id}">{cat.name}</option>
                </q:loop>
            </select>
        </q:success>
    </q:fetch>

    <!-- Cache for 1 hour -->
    <q:fetch name="settings"
             url="/api/settings"
             method="GET"
             cache="1h">
        <q:success>
            <div>Theme: {settings.theme}</div>
        </q:success>
    </q:fetch>

    <!-- Cache for 30 seconds -->
    <q:fetch name="stats"
             url="/api/stats"
             method="GET"
             cache="30s">
        <q:success>
            <div>Active users: {stats.activeUsers}</div>
        </q:success>
    </q:fetch>
</q:component>
