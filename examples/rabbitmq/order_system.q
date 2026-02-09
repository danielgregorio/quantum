<?xml version="1.0" encoding="UTF-8"?>
<!--
RabbitMQ Order Processing System

This example demonstrates a complete order processing system using
RabbitMQ for message queuing. It includes:
- Order creation with event publishing
- Inventory service subscribing to order events
- Payment service processing payments
- Notification service sending emails

To run:
  set MESSAGE_BROKER_TYPE=rabbitmq
  python src/cli/runner.py run examples/rabbitmq/order_system.q
-->
<q:component xmlns:q="https://quantum.lang/ns" name="OrderProcessingSystem">

    <!-- Declare queues with dead letter support -->
    <q:queue name="orders.process"
             action="declare"
             durable="true"
             deadLetterQueue="orders.dlq" />

    <q:queue name="payments.process"
             action="declare"
             durable="true"
             deadLetterQueue="payments.dlq" />

    <q:queue name="notifications.send"
             action="declare"
             durable="true" />

    <q:queue name="inventory.update"
             action="declare"
             durable="true" />

    <!-- State -->
    <q:set name="orderCount" value="0" />
    <q:set name="lastOrderId" value="" />

    <!-- Create Order Action -->
    <q:action name="createOrder">
        <!-- Generate order ID -->
        <q:set name="orderId" value="ORD-{uuid()}" />
        <q:set name="orderCount" operation="increment" />

        <!-- In production: save to database -->
        <q:log level="info">Creating order: {orderId}</q:log>

        <!-- Publish order created event to topic -->
        <q:message topic="orders.created" type="publish">
            <q:header name="priority" value="high" />
            <q:header name="source" value="web" />
            <q:body>
                {
                    "orderId": "{orderId}",
                    "customerId": "{form.customerId}",
                    "items": {form.items},
                    "total": {form.total},
                    "status": "pending",
                    "createdAt": "{now()}"
                }
            </q:body>
        </q:message>

        <!-- Send to processing queue -->
        <q:message queue="orders.process" type="send">
            <q:header name="orderId" value="{orderId}" />
            <q:body>
                {
                    "orderId": "{orderId}",
                    "action": "process",
                    "items": {form.items},
                    "total": {form.total}
                }
            </q:body>
        </q:message>

        <q:set name="lastOrderId" value="{orderId}" />

        <div class="alert alert-success">
            <strong>Order Created!</strong>
            <p>Order ID: {orderId}</p>
            <p>Processing has been queued.</p>
        </div>
    </q:action>

    <!-- Process Payment Action -->
    <q:action name="processPayment">
        <q:log level="info">Processing payment for order: {form.orderId}</q:log>

        <!-- Send payment request -->
        <q:message queue="payments.process" type="send">
            <q:header name="orderId" value="{form.orderId}" />
            <q:body>
                {
                    "orderId": "{form.orderId}",
                    "amount": {form.amount},
                    "method": "{form.method}",
                    "currency": "BRL"
                }
            </q:body>
        </q:message>

        <!-- Publish event -->
        <q:message topic="payments.initiated" type="publish">
            <q:body>
                {
                    "orderId": "{form.orderId}",
                    "amount": {form.amount},
                    "status": "initiated"
                }
            </q:body>
        </q:message>

        <div class="alert alert-info">
            Payment processing initiated for order {form.orderId}.
        </div>
    </q:action>

    <!-- Request Shipping Quote (Request/Reply Pattern) -->
    <q:action name="getShippingQuote">
        <q:message name="shippingQuote"
                   queue="shipping.quotes"
                   type="request"
                   timeout="10s">
            <q:body>
                {
                    "address": "{form.address}",
                    "zipCode": "{form.zipCode}",
                    "weight": {form.weight},
                    "dimensions": "{form.dimensions}"
                }
            </q:body>
        </q:message>

        <q:if condition="{shippingQuote}">
            <div class="card">
                <div class="card-header">Shipping Quote</div>
                <div class="card-body">
                    <p>Cost: R$ {shippingQuote.cost}</p>
                    <p>Delivery: {shippingQuote.days} business days</p>
                    <p>Carrier: {shippingQuote.carrier}</p>
                </div>
            </div>
        </q:if>
        <q:else>
            <div class="alert alert-warning">
                Unable to get shipping quote at this time.
            </div>
        </q:else>
    </q:action>

    <!-- Subscribe to Order Events (Inventory Service) -->
    <q:subscribe topic="orders.created" name="inventory-watcher">
        <q:onMessage>
            <q:log level="info">
                [Inventory] Order received: {message.body.orderId}
            </q:log>

            <!-- Update inventory (in production: database update) -->
            <q:message queue="inventory.update" type="send">
                <q:body>
                    {
                        "action": "reserve",
                        "orderId": "{message.body.orderId}",
                        "items": {message.body.items}
                    }
                </q:body>
            </q:message>
        </q:onMessage>

        <q:onError>
            <q:log level="error">
                [Inventory] Error processing order: {error.message}
            </q:log>
        </q:onError>
    </q:subscribe>

    <!-- Subscribe to Payment Events -->
    <q:subscribe topic="payments.*" name="payment-logger">
        <q:onMessage>
            <q:log level="info">
                [Payment] Event: {message.topic} for order {message.body.orderId}
            </q:log>
        </q:onMessage>
    </q:subscribe>

    <!-- Queue Consumer: Order Processor -->
    <q:subscribe queue="orders.process"
                 name="order-processor"
                 ack="manual"
                 prefetch="5">
        <q:onMessage>
            <q:log level="info">
                [Processor] Processing order: {message.body.orderId}
            </q:log>

            <!-- Simulate processing -->
            <q:set name="processingSuccess" value="true" />

            <q:if condition="{processingSuccess}">
                <!-- Acknowledge success -->
                <q:messageAck />

                <!-- Publish completion event -->
                <q:message topic="orders.processed" type="publish">
                    <q:body>
                        {
                            "orderId": "{message.body.orderId}",
                            "status": "processed",
                            "processedAt": "{now()}"
                        }
                    </q:body>
                </q:message>

                <!-- Queue notification -->
                <q:message queue="notifications.send" type="send">
                    <q:body>
                        {
                            "type": "order_processed",
                            "orderId": "{message.body.orderId}",
                            "template": "order_confirmation"
                        }
                    </q:body>
                </q:message>
            </q:if>
            <q:else>
                <!-- Requeue for retry -->
                <q:messageNack requeue="true" />
            </q:else>
        </q:onMessage>

        <q:onError>
            <q:log level="error">
                [Processor] Order processing failed: {error.message}
            </q:log>
            <!-- Send to DLQ -->
            <q:messageNack requeue="false" />
        </q:onError>
    </q:subscribe>

    <!-- Queue Stats Action -->
    <q:action name="checkQueues">
        <q:queue name="orders.process" action="info" result="ordersQueue" />
        <q:queue name="payments.process" action="info" result="paymentsQueue" />
        <q:queue name="notifications.send" action="info" result="notificationsQueue" />

        <div class="card">
            <div class="card-header">Queue Statistics</div>
            <div class="card-body">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Queue</th>
                            <th>Messages</th>
                            <th>Consumers</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>orders.process</td>
                            <td>{ordersQueue.messageCount}</td>
                            <td>{ordersQueue.consumerCount}</td>
                        </tr>
                        <tr>
                            <td>payments.process</td>
                            <td>{paymentsQueue.messageCount}</td>
                            <td>{paymentsQueue.consumerCount}</td>
                        </tr>
                        <tr>
                            <td>notifications.send</td>
                            <td>{notificationsQueue.messageCount}</td>
                            <td>{notificationsQueue.consumerCount}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </q:action>

    <!-- Purge Dead Letter Queue Action -->
    <q:action name="purgeDLQ">
        <q:queue name="orders.dlq" action="purge" result="purgeResult" />
        <div class="alert alert-success">
            Purged {purgeResult} messages from dead letter queue.
        </div>
    </q:action>

    <!-- UI -->
    <div class="container mt-4">
        <h1>Order Processing System</h1>
        <p class="text-muted">RabbitMQ Message Queue Demo</p>

        <div class="row">
            <!-- Create Order Form -->
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header">Create Order</div>
                    <div class="card-body">
                        <form action="createOrder" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Customer ID</label>
                                <input type="text" name="customerId" class="form-control"
                                       placeholder="CUST-001" required />
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Items (JSON)</label>
                                <textarea name="items" class="form-control" rows="3"
                                          placeholder='[{"sku": "PROD-001", "qty": 2}]'
                                          required></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Total (BRL)</label>
                                <input type="number" name="total" class="form-control"
                                       step="0.01" placeholder="199.90" required />
                            </div>
                            <button type="submit" class="btn btn-primary">
                                Create Order
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Process Payment Form -->
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header">Process Payment</div>
                    <div class="card-body">
                        <form action="processPayment" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Order ID</label>
                                <input type="text" name="orderId" class="form-control"
                                       value="{lastOrderId}" placeholder="ORD-..." required />
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Amount</label>
                                <input type="number" name="amount" class="form-control"
                                       step="0.01" placeholder="199.90" required />
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Payment Method</label>
                                <select name="method" class="form-select">
                                    <option value="pix">PIX</option>
                                    <option value="credit_card">Credit Card</option>
                                    <option value="boleto">Boleto</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-success">
                                Process Payment
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- Shipping Quote -->
        <div class="card mb-4">
            <div class="card-header">Shipping Quote (RPC)</div>
            <div class="card-body">
                <form action="getShippingQuote" method="POST" class="row g-3">
                    <div class="col-md-4">
                        <input type="text" name="address" class="form-control"
                               placeholder="Street Address" required />
                    </div>
                    <div class="col-md-2">
                        <input type="text" name="zipCode" class="form-control"
                               placeholder="CEP" required />
                    </div>
                    <div class="col-md-2">
                        <input type="number" name="weight" class="form-control"
                               step="0.1" placeholder="Weight (kg)" required />
                    </div>
                    <div class="col-md-2">
                        <input type="text" name="dimensions" class="form-control"
                               placeholder="30x20x10" required />
                    </div>
                    <div class="col-md-2">
                        <button type="submit" class="btn btn-outline-primary w-100">
                            Get Quote
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Queue Management -->
        <div class="card">
            <div class="card-header">Queue Management</div>
            <div class="card-body">
                <button type="button" class="btn btn-info" onclick="checkQueues()">
                    Check Queue Stats
                </button>
                <button type="button" class="btn btn-danger" onclick="purgeDLQ()">
                    Purge DLQ
                </button>
            </div>
        </div>

        <!-- Stats -->
        <div class="mt-4 text-center text-muted">
            <p>Orders created this session: {orderCount}</p>
        </div>
    </div>
</q:component>
