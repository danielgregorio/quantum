<?xml version="1.0" encoding="UTF-8"?>
<!--
  Quantum Message Queue System Demo

  This example demonstrates the message queue functionality:
  - Publishing messages to topics
  - Sending messages to queues
  - Request/reply pattern
  - Queue management
  - Subscriptions

  By default, uses in-memory broker (no external dependencies).
  Set MESSAGE_BROKER_TYPE=redis or rabbitmq for production use.
-->
<q:component name="MessageQueueDemo" xmlns:q="https://quantum.lang/ns">

  <!-- Queue Management -->

  <!-- Declare a durable queue for order processing -->
  <q:queue name="orders" action="declare" durable="true" />

  <!-- Declare a queue with dead letter queue and TTL -->
  <q:queue name="notifications" action="declare"
           durable="true"
           deadLetterQueue="notifications-dlq"
           ttl="86400000" />

  <!-- Declare the dead letter queue -->
  <q:queue name="notifications-dlq" action="declare" durable="true" />


  <!-- Publishing to Topics (Pub/Sub) -->

  <q:set name="orderData" type="object" value='{"orderId": "ORD-001", "product": "Widget", "quantity": 5}' />

  <!-- Publish order created event -->
  <q:message name="publishResult" topic="orders.created" type="publish">
    <q:header name="priority" value="high" />
    <q:header name="source" value="web-app" />
    <q:body>{orderData}</q:body>
  </q:message>

  <q:log level="info" message="Published to topic: orders.created, result: {publishResult.success}" />


  <!-- Sending to Queues (Point-to-Point) -->

  <q:set name="emailTask" type="object" value='{"to": "customer@example.com", "subject": "Order Confirmation", "orderId": "ORD-001"}' />

  <!-- Send email task to queue -->
  <q:message name="sendResult" queue="notifications" type="send">
    <q:header name="type" value="email" />
    <q:body>{emailTask}</q:body>
  </q:message>

  <q:log level="info" message="Sent to queue: notifications, messageId: {sendResult.message_id}" />


  <!-- Request/Reply Pattern -->

  <q:set name="calcRequest" type="object" value='{"operation": "add", "a": 10, "b": 25}' />

  <!--
    Note: Request/reply requires a consumer on the calculator queue.
    This is just demonstrating the syntax - in a real scenario,
    you would have a worker component processing these requests.
  -->
  <!--
  <q:message name="calcResponse" queue="calculator" type="request" timeout="5000">
    <q:body>{calcRequest}</q:body>
  </q:message>

  <q:if condition="{calcResponse.success}">
    <q:log level="info" message="Calculation result: {calcResponse.data.result}" />
  </q:if>
  -->


  <!-- Queue Info -->

  <q:queue name="notifications" action="info" result="queueInfo" />

  <q:log level="info" message="Queue 'notifications' has {queueInfo.message_count} messages and {queueInfo.consumer_count} consumers" />


  <!-- Subscribing to Topics (Async) -->

  <!--
    Note: Subscriptions run asynchronously. The onMessage handler
    is called each time a message is received.
  -->
  <!--
  <q:subscribe name="orderSubscription" topic="orders.*" ack="auto">
    <q:onMessage>
      <q:log level="info" message="Received order event on topic: {message.topic}" />
      <q:set name="orderBody" value="{message.body}" />
      <q:log level="info" message="Order data: {orderBody}" />
    </q:onMessage>
    <q:onError>
      <q:log level="error" message="Error processing order: {error}" />
    </q:onError>
  </q:subscribe>
  -->


  <!-- Queue Consumer with Manual Ack -->

  <!--
    Manual acknowledgment allows you to control when a message
    is considered processed. Useful for ensuring reliable processing.
  -->
  <!--
  <q:subscribe name="emailWorker" queue="notifications" ack="manual" prefetch="5">
    <q:onMessage>
      <q:set name="task" value="{message.body}" />

      <q:if condition="{task.type} == 'email'">
        <q:mail
          to="{task.to}"
          subject="{task.subject}"
          type="html">
          <p>Your order {task.orderId} has been confirmed!</p>
        </q:mail>

        <q:messageAck />
      </q:if>
      <q:else>
        <q:log level="warn" message="Unknown task type: {task.type}" />
        <q:messageNack requeue="false" />
      </q:else>
    </q:onMessage>
    <q:onError>
      <q:log level="error" message="Email worker error: {error}" />
      <q:messageNack requeue="true" />
    </q:onError>
  </q:subscribe>
  -->


  <!-- Summary -->

  <q:set name="summary" type="object" value='{}' />
  <q:set name="summary" operation="setProperty" key="demo" value="Message Queue System" />
  <q:set name="summary" operation="setProperty" key="publishResult" value="{publishResult.success}" />
  <q:set name="summary" operation="setProperty" key="sendResult" value="{sendResult.success}" />

  <q:return value="{summary}" />

</q:component>
