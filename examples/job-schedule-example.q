<?xml version="1.0" encoding="UTF-8"?>
<!--
Example: Job Scheduling with q:schedule
Demonstrates scheduled task execution similar to ColdFusion's cfschedule
-->
<q:component xmlns:q="https://quantum.lang/ns" name="ScheduleExample">
    <!-- Schedule a task to run every 5 minutes -->
    <q:schedule name="cleanup-sessions"
                interval="5m"
                enabled="true">
        <q:query datasource="db">
            DELETE FROM sessions WHERE expires_at < NOW()
        </q:query>
        <q:log level="info">Session cleanup completed</q:log>
    </q:schedule>

    <!-- Schedule a task using cron expression (daily at 8 AM) -->
    <q:schedule name="daily-report"
                cron="0 8 * * *"
                timezone="America/Sao_Paulo">
        <q:query name="stats" datasource="db">
            SELECT
                COUNT(*) as total_orders,
                SUM(total) as revenue
            FROM orders
            WHERE DATE(created_at) = CURDATE() - INTERVAL 1 DAY
        </q:query>

        <q:mail to="admin@company.com" subject="Daily Sales Report">
            <q:body>
                Daily Report - {formatDate(now(), 'yyyy-MM-dd')}

                Orders: {stats.total_orders}
                Revenue: ${formatNumber(stats.revenue, '0.00')}
            </q:body>
        </q:mail>

        <q:log level="info">Daily report sent</q:log>
    </q:schedule>

    <!-- One-time scheduled task -->
    <q:schedule name="send-reminder"
                at="2025-03-01T10:00:00"
                action="run">
        <q:invoke function="sendReminderEmails" />
    </q:schedule>

    <!-- Control existing schedules -->
    <q:action name="pauseCleanup">
        <q:schedule name="cleanup-sessions" action="pause" />
        <p>Cleanup schedule paused</p>
    </q:action>

    <q:action name="resumeCleanup">
        <q:schedule name="cleanup-sessions" action="resume" />
        <p>Cleanup schedule resumed</p>
    </q:action>

    <!-- Functions used by schedules -->
    <q:function name="sendReminderEmails">
        <q:query name="users" datasource="db">
            SELECT email, name FROM users
            WHERE reminder_sent = false
            AND created_at < NOW() - INTERVAL 7 DAY
        </q:query>

        <q:loop type="query" var="user" items="{users}">
            <q:mail to="{user.email}" subject="We miss you!">
                <q:body>
                    Hi {user.name},

                    We noticed you haven't visited in a while...
                </q:body>
            </q:mail>

            <q:query datasource="db">
                UPDATE users SET reminder_sent = true WHERE email = :email
                <q:param name="email" value="{user.email}" />
            </q:query>
        </q:loop>

        <q:return value="{users.recordCount} reminders sent" />
    </q:function>
</q:component>
