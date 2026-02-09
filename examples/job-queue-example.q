<?xml version="1.0" encoding="UTF-8"?>
<!--
Example: Job Queue with q:job
Demonstrates job queue for batch processing with retries
-->
<q:component xmlns:q="https://quantum.lang/ns" name="JobQueueExample">
    <!-- Define a job handler -->
    <q:job name="process-order"
           queue="orders"
           attempts="3"
           backoff="30s"
           timeout="5m">
        <q:param name="orderId" type="integer" required="true" />

        <!-- Fetch order details -->
        <q:query name="order" datasource="db">
            SELECT * FROM orders WHERE id = :orderId
            <q:param name="orderId" value="{orderId}" type="integer" />
        </q:query>

        <q:if condition="{order.recordCount == 0}">
            <q:throw message="Order not found: {orderId}" />
        </q:if>

        <!-- Process payment -->
        <q:invoke name="payment"
                  url="https://payment.api/charge"
                  method="POST">
            <q:body>
                {
                    "orderId": {order.id},
                    "amount": {order.total},
                    "currency": "BRL"
                }
            </q:body>
        </q:invoke>

        <q:if condition="{payment.success}">
            <!-- Update order status -->
            <q:query datasource="db">
                UPDATE orders SET status = 'paid', paid_at = NOW()
                WHERE id = :orderId
                <q:param name="orderId" value="{orderId}" type="integer" />
            </q:query>

            <!-- Send confirmation email -->
            <q:mail to="{order.customer_email}" subject="Order Confirmed">
                <q:body>
                    Your order #{orderId} has been confirmed!
                    Total: ${order.total}
                </q:body>
            </q:mail>

            <q:log level="info">Order {orderId} processed successfully</q:log>
        </q:if>
        <q:else>
            <q:throw message="Payment failed: {payment.error}" />
        </q:else>
    </q:job>

    <!-- Define another job -->
    <q:job name="send-notification"
           queue="notifications"
           attempts="5"
           backoff="10s">
        <q:param name="userId" type="integer" required="true" />
        <q:param name="message" type="string" required="true" />
        <q:param name="type" type="string" default="info" />

        <q:query name="user" datasource="db">
            SELECT * FROM users WHERE id = :userId
            <q:param name="userId" value="{userId}" type="integer" />
        </q:query>

        <q:invoke name="push"
                  url="https://push.service/send"
                  method="POST">
            <q:body>
                {
                    "token": "{user.push_token}",
                    "title": "Notification",
                    "body": "{message}",
                    "data": {"type": "{type}"}
                }
            </q:body>
        </q:invoke>
    </q:job>

    <!-- Dispatch jobs from actions -->
    <q:action name="submitOrder">
        <q:query name="newOrder" datasource="db">
            INSERT INTO orders (customer_id, items, total)
            VALUES (:customerId, :items, :total)
        </q:query>

        <!-- Dispatch job immediately -->
        <q:job name="process-order" action="dispatch">
            <q:param name="orderId" value="{newOrder.insertId}" />
        </q:job>

        <q:redirect to="/orders/{newOrder.insertId}" />
    </q:action>

    <!-- Dispatch with delay -->
    <q:action name="scheduleReminder">
        <q:job name="send-notification" action="dispatch" delay="1h">
            <q:param name="userId" value="{session.userId}" />
            <q:param name="message" value="Don't forget to complete your order!" />
            <q:param name="type" value="reminder" />
        </q:job>

        <p>Reminder scheduled for 1 hour from now</p>
    </q:action>

    <!-- Batch dispatch -->
    <q:action name="notifyAllUsers">
        <q:query name="users" datasource="db">
            SELECT id FROM users WHERE notifications_enabled = true
        </q:query>

        <q:job name="send-notification" action="batch">
            <q:loop type="query" var="user" items="{users}">
                <q:param name="userId" value="{user.id}" />
                <q:param name="message" value="{form.message}" />
            </q:loop>
        </q:job>

        <p>Scheduled {users.recordCount} notifications</p>
    </q:action>

    <!-- UI -->
    <div>
        <h2>Order Processing</h2>

        <form action="submitOrder" method="POST">
            <input type="hidden" name="customerId" value="{session.userId}" />
            <input type="text" name="items" placeholder="Items JSON" />
            <input type="number" name="total" placeholder="Total" />
            <button type="submit">Submit Order</button>
        </form>

        <h3>Bulk Notification</h3>
        <form action="notifyAllUsers" method="POST">
            <textarea name="message" placeholder="Message to all users"></textarea>
            <button type="submit">Send to All</button>
        </form>
    </div>
</q:component>
