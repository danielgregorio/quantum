<?xml version="1.0" encoding="UTF-8"?>
<!--
Example: Message Queue with q:message and q:subscribe
Demonstrates pub/sub and queue-based messaging
-->
<q:component xmlns:q="https://quantum.lang/ns" name="MessageQueueExample">
    <!-- Declare queues -->
    <q:queue name="orders" durable="true">
        <q:dead-letter queue="orders.dlq" />
        <q:ttl value="86400000" />  <!-- 24 hours -->
    </q:queue>

    <q:queue name="notifications" durable="true" />
    <q:queue name="orders.dlq" durable="true" />

    <!-- Publish to topic when order is created -->
    <q:action name="createOrder">
        <q:query name="order" datasource="db">
            INSERT INTO orders (customer_id, items, total)
            VALUES (:customerId, :items, :total)
        </q:query>

        <!-- Publish event to topic -->
        <q:message topic="orders.created" type="publish">
            <q:header name="priority" value="high" />
            <q:header name="source" value="web" />
            <q:body>
                {
                    "orderId": {order.insertId},
                    "customerId": {form.customerId},
                    "items": {form.items},
                    "total": {form.total},
                    "createdAt": "{now()}"
                }
            </q:body>
        </q:message>

        <q:redirect to="/orders/{order.insertId}" />
    </q:action>

    <!-- Subscribe to order events (different service) -->
    <q:subscribe topic="orders.created" name="order-handler">
        <q:on-message>
            <q:log level="info">Received order: {message.body.orderId}</q:log>

            <!-- Process the order -->
            <q:invoke function="processOrder">
                <q:arg name="orderId" value="{message.body.orderId}" />
            </q:invoke>
        </q:on-message>

        <q:on-error>
            <q:log level="error">Order processing failed: {error.message}</q:log>

            <!-- Send to dead letter queue -->
            <q:message queue="orders.dlq" type="send">
                <q:header name="original-topic" value="{message.topic}" />
                <q:header name="error" value="{error.message}" />
                <q:body>{message.body}</q:body>
            </q:message>
        </q:on-error>
    </q:subscribe>

    <!-- Subscribe to multiple topics with pattern -->
    <q:subscribe topics="orders.*, payments.*" name="audit-logger">
        <q:on-message>
            <q:query datasource="db">
                INSERT INTO audit_log (topic, payload, timestamp)
                VALUES (:topic, :payload, NOW())
                <q:param name="topic" value="{message.topic}" />
                <q:param name="payload" value="{JSON.stringify(message.body)}" type="text" />
            </q:query>
        </q:on-message>
    </q:subscribe>

    <!-- Direct queue messaging -->
    <q:action name="sendNotification">
        <q:message queue="notifications" type="send">
            <q:header name="user-id" value="{form.userId}" />
            <q:body>
                {
                    "userId": {form.userId},
                    "title": "{form.title}",
                    "message": "{form.message}"
                }
            </q:body>
        </q:message>

        <p>Notification queued</p>
    </q:action>

    <!-- Queue consumer with manual acknowledgment -->
    <q:subscribe queue="notifications"
                 name="notification-worker"
                 ack="manual"
                 prefetch="10">
        <q:on-message>
            <q:query name="user" datasource="db">
                SELECT * FROM users WHERE id = :userId
                <q:param name="userId" value="{message.body.userId}" type="integer" />
            </q:query>

            <q:if condition="{user.recordCount > 0}">
                <!-- Send push notification -->
                <q:invoke name="push"
                          url="https://push.service/send"
                          method="POST">
                    <q:body>
                        {
                            "token": "{user.push_token}",
                            "title": "{message.body.title}",
                            "body": "{message.body.message}"
                        }
                    </q:body>
                </q:invoke>

                <q:if condition="{push.success}">
                    <!-- Acknowledge success -->
                    <q:message-ack />
                </q:if>
                <q:else>
                    <!-- Requeue for retry -->
                    <q:message-nack requeue="true" />
                </q:else>
            </q:if>
            <q:else>
                <!-- User not found, don't requeue -->
                <q:message-nack requeue="false" />
            </q:else>
        </q:on-message>

        <q:on-error>
            <q:log level="error">Notification failed: {error.message}</q:log>
            <q:message-nack requeue="true" />
        </q:on-error>
    </q:subscribe>

    <!-- Request/Reply pattern -->
    <q:action name="calculateShipping">
        <q:message name="shippingResult"
                   queue="shipping-calculator"
                   type="request"
                   timeout="10s">
            <q:body>
                {
                    "address": "{form.address}",
                    "items": {cart.items},
                    "weight": {cart.totalWeight}
                }
            </q:body>
        </q:message>

        <q:if condition="{shippingResult}">
            <p>Shipping cost: ${shippingResult.cost}</p>
            <p>Estimated delivery: {shippingResult.estimatedDays} days</p>
        </q:if>
        <q:else>
            <p>Unable to calculate shipping at this time.</p>
        </q:else>
    </q:action>

    <!-- Queue management -->
    <q:action name="purgeDeadLetters">
        <q:queue name="orders.dlq" action="purge" />
        <p>Dead letter queue purged</p>
    </q:action>

    <q:action name="checkQueueStats">
        <q:queue name="orders" action="info" result="queueInfo" />
        <p>Messages in queue: {queueInfo.messageCount}</p>
        <p>Active consumers: {queueInfo.consumerCount}</p>
    </q:action>

    <!-- UI -->
    <div>
        <h2>Message Queue Demo</h2>

        <h3>Create Order</h3>
        <form action="createOrder" method="POST">
            <input type="number" name="customerId" placeholder="Customer ID" />
            <textarea name="items" placeholder="Items JSON"></textarea>
            <input type="number" name="total" placeholder="Total" step="0.01" />
            <button type="submit">Create Order</button>
        </form>

        <h3>Send Notification</h3>
        <form action="sendNotification" method="POST">
            <input type="number" name="userId" placeholder="User ID" />
            <input type="text" name="title" placeholder="Title" />
            <textarea name="message" placeholder="Message"></textarea>
            <button type="submit">Send</button>
        </form>

        <h3>Queue Management</h3>
        <button onclick="checkQueueStats()">Check Stats</button>
        <button onclick="purgeDeadLetters()">Purge DLQ</button>
    </div>

    <!-- Helper functions -->
    <q:function name="processOrder">
        <q:param name="orderId" type="integer" />

        <q:query name="order" datasource="db">
            SELECT * FROM orders WHERE id = :orderId
        </q:query>

        <!-- Process payment -->
        <q:invoke name="payment" url="https://payment.api/charge" method="POST">
            <q:body>{order}</q:body>
        </q:invoke>

        <q:if condition="{payment.success}">
            <!-- Publish payment completed event -->
            <q:message topic="payments.completed" type="publish">
                <q:body>
                    {
                        "orderId": {orderId},
                        "transactionId": "{payment.transactionId}"
                    }
                </q:body>
            </q:message>
        </q:if>
        <q:else>
            <q:message topic="payments.failed" type="publish">
                <q:body>
                    {
                        "orderId": {orderId},
                        "error": "{payment.error}"
                    }
                </q:body>
            </q:message>
        </q:else>
    </q:function>
</q:component>
