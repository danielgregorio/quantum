<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: Polling fetch
Tests: Automatic refetch at intervals
-->
<q:component xmlns:q="https://quantum.lang/ns" name="fetch-polling">
    <!-- Poll for notifications every 30 seconds -->
    <q:fetch name="notifications"
             url="/api/notifications"
             method="GET"
             interval="30s">
        <q:success>
            <div class="notification-badge">
                <span>{notifications.unread}</span> unread
            </div>
            <ul class="notifications">
                <q:loop var="notif" items="{notifications.items}">
                    <li class="{notif.read ? '' : 'unread'}">{notif.message}</li>
                </q:loop>
            </ul>
        </q:success>
    </q:fetch>

    <!-- Poll for live data every 5 seconds -->
    <q:fetch name="liveStats"
             url="/api/dashboard/live"
             method="GET"
             interval="5s"
             cache="0">
        <q:success>
            <div class="live-stats">
                <div class="stat">
                    <span class="value">{liveStats.visitors}</span>
                    <span class="label">Active Visitors</span>
                </div>
                <div class="stat">
                    <span class="value">{liveStats.orders}</span>
                    <span class="label">Orders Today</span>
                </div>
            </div>
        </q:success>
    </q:fetch>
</q:component>
