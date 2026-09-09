# Proposta: Message Queue Integration

## Visao Geral

Integracao nativa com sistemas de filas de mensagens (RabbitMQ, AWS SQS, Redis Pub/Sub) para comunicacao assincrona entre componentes e servicos.

## Motivacao

O Quantum precisa de um mecanismo robusto para:
- Comunicacao assincrona entre microservicos
- Desacoplamento de componentes
- Processamento distribuido
- Event-driven architecture

**Referencia:**
- `src/runtime/component.py:1300` - `# TODO: integrate with actual message queue`
- `src/runtime/component.py:1309` - `# TODO: Integrate with RabbitMQ/SQS/etc`

## Componentes Propostos

### 1. `q:message` - Publicar Mensagens

```xml
<!-- Publicar em um topico -->
<q:message topic="orders.created" type="publish">
    <q:body>
        {
            "orderId": {order.id},
            "customerId": {customer.id},
            "total": {order.total}
        }
    </q:body>
</q:message>

<!-- Publicar com headers -->
<q:message topic="notifications" type="publish">
    <q:header name="priority" value="high" />
    <q:header name="retry-count" value="0" />
    <q:body>{notification}</q:body>
</q:message>

<!-- Publicar para queue especifica (RabbitMQ) -->
<q:message queue="email-queue" type="send">
    <q:body>
        {
            "to": "{user.email}",
            "subject": "Welcome!",
            "template": "welcome"
        }
    </q:body>
</q:message>

<!-- Request-Reply pattern -->
<q:message name="response"
           queue="calculation-queue"
           type="request"
           timeout="30s">
    <q:body>{"numbers": [1, 2, 3, 4, 5]}</q:body>
</q:message>

<p>Sum result: {response.result}</p>
```

### 2. `q:subscribe` - Consumir Mensagens

```xml
<!-- Subscriber simples -->
<q:subscribe topic="orders.created" name="order-handler">
    <q:on-message>
        <q:set name="order" value="{message.body}" />

        <q:invoke function="processOrder">
            <q:arg name="orderId" value="{order.orderId}" />
        </q:invoke>

        <q:log level="info">Processed order {order.orderId}</q:log>
    </q:on-message>

    <q:on-error>
        <q:log level="error">Failed to process: {error.message}</q:log>
        <!-- Opcional: enviar para dead letter queue -->
        <q:message queue="orders.dlq" type="send">
            <q:body>{message}</q:body>
        </q:message>
    </q:on-error>
</q:subscribe>

<!-- Consumer de queue com acknowledgment manual -->
<q:subscribe queue="email-queue"
             name="email-worker"
             ack="manual"
             prefetch="10">
    <q:on-message>
        <q:mail to="{message.body.to}"
                subject="{message.body.subject}">
            <q:body template="{message.body.template}" />
        </q:mail>

        <!-- Acknowledge after success -->
        <q:message-ack />
    </q:on-message>

    <q:on-error>
        <!-- Negative acknowledge - requeue -->
        <q:message-nack requeue="true" />
    </q:on-error>
</q:subscribe>

<!-- Multiple topics subscription -->
<q:subscribe topics="orders.*, payments.*" name="audit-logger">
    <q:on-message>
        <q:query datasource="db">
            INSERT INTO audit_log (topic, payload, timestamp)
            VALUES (:topic, :payload, NOW())
            <q:param name="topic" value="{message.topic}" />
            <q:param name="payload" value="{message.body}" type="json" />
        </q:query>
    </q:on-message>
</q:subscribe>
```

### 3. `q:queue` - Gerenciamento de Filas

```xml
<!-- Declarar uma fila -->
<q:queue name="orders"
         durable="true"
         exclusive="false"
         auto-delete="false">
    <q:dead-letter queue="orders.dlq" />
    <q:ttl value="86400000" />  <!-- 24 horas -->
</q:queue>

<!-- Declarar exchange (RabbitMQ) -->
<q:exchange name="events"
            type="topic"
            durable="true">
    <q:bind queue="order-processing" routing-key="orders.*" />
    <q:bind queue="audit-log" routing-key="#" />
</q:exchange>

<!-- Purge queue -->
<q:queue name="test-queue" action="purge" />

<!-- Delete queue -->
<q:queue name="temp-queue" action="delete" />

<!-- Get queue info -->
<q:queue name="orders" action="info" result="queueInfo" />
<p>Messages: {queueInfo.messageCount}</p>
```

## Arquitetura

### Componentes Internos

```
┌─────────────────────────────────────────────────────────────┐
│                      Quantum Runtime                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Message Broker Abstraction             │ │
│  │                                                         │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │
│  │  │  RabbitMQ   │ │   AWS SQS   │ │ Redis Pub/  │       │ │
│  │  │   Adapter   │ │   Adapter   │ │ Sub Adapter │       │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘       │ │
│  │                                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                              │                               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   Message Handlers                      │ │
│  │                                                         │ │
│  │   - Parse q:message/q:subscribe/q:queue nodes          │ │
│  │   - Serialize/deserialize messages                      │ │
│  │   - Handle acknowledgments                              │ │
│  │   - Error handling and DLQ                              │ │
│  │                                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Broker Abstraction

```python
# src/runtime/message_broker.py

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Message:
    """Mensagem padronizada"""
    id: str
    topic: Optional[str] = None
    queue: Optional[str] = None
    body: Any = None
    headers: Dict[str, str] = None
    timestamp: float = None
    routing_key: Optional[str] = None

class MessageBroker(ABC):
    """Interface abstrata para message brokers"""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """Conectar ao broker"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Desconectar do broker"""
        pass

    @abstractmethod
    def publish(self, topic: str, message: Message) -> None:
        """Publicar em um topico"""
        pass

    @abstractmethod
    def send(self, queue: str, message: Message) -> None:
        """Enviar para uma fila"""
        pass

    @abstractmethod
    def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        """Subscrever em um topico"""
        pass

    @abstractmethod
    def consume(self, queue: str, handler: Callable[[Message], None]) -> str:
        """Consumir de uma fila"""
        pass

    @abstractmethod
    def ack(self, message: Message) -> None:
        """Acknowledge message"""
        pass

    @abstractmethod
    def nack(self, message: Message, requeue: bool = True) -> None:
        """Negative acknowledge"""
        pass

    @abstractmethod
    def declare_queue(self, name: str, **options) -> None:
        """Declarar uma fila"""
        pass

    @abstractmethod
    def declare_exchange(self, name: str, type: str, **options) -> None:
        """Declarar um exchange"""
        pass
```

### RabbitMQ Adapter

```python
# src/runtime/adapters/rabbitmq_adapter.py

import pika
import json
from .message_broker import MessageBroker, Message

class RabbitMQAdapter(MessageBroker):
    def __init__(self):
        self.connection = None
        self.channel = None
        self.consumers = {}

    def connect(self, config: Dict[str, Any]) -> None:
        credentials = pika.PlainCredentials(
            config.get('username', 'guest'),
            config.get('password', 'guest')
        )
        parameters = pika.ConnectionParameters(
            host=config.get('host', 'localhost'),
            port=config.get('port', 5672),
            virtual_host=config.get('vhost', '/'),
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def disconnect(self) -> None:
        if self.channel:
            self.channel.close()
        if self.connection:
            self.connection.close()

    def publish(self, topic: str, message: Message) -> None:
        # Topic exchange
        exchange = topic.split('.')[0] if '.' in topic else 'amq.topic'
        routing_key = topic

        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message.body),
            properties=pika.BasicProperties(
                headers=message.headers,
                message_id=message.id,
                timestamp=int(message.timestamp or time.time()),
                content_type='application/json',
                delivery_mode=2  # Persistent
            )
        )

    def send(self, queue: str, message: Message) -> None:
        self.channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=json.dumps(message.body),
            properties=pika.BasicProperties(
                headers=message.headers,
                message_id=message.id,
                content_type='application/json',
                delivery_mode=2
            )
        )

    def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        # Create temporary queue for subscription
        result = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue

        # Bind to exchange
        exchange = topic.split('.')[0] if '.' in topic else 'amq.topic'
        self.channel.queue_bind(
            exchange=exchange,
            queue=queue_name,
            routing_key=topic
        )

        def callback(ch, method, properties, body):
            message = Message(
                id=properties.message_id,
                topic=method.routing_key,
                body=json.loads(body),
                headers=properties.headers
            )
            handler(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        consumer_tag = self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback
        )
        self.consumers[consumer_tag] = queue_name
        return consumer_tag

    def consume(self, queue: str, handler: Callable[[Message], None]) -> str:
        def callback(ch, method, properties, body):
            message = Message(
                id=properties.message_id,
                queue=queue,
                body=json.loads(body),
                headers=properties.headers
            )
            message._delivery_tag = method.delivery_tag
            message._channel = ch
            handler(message)

        consumer_tag = self.channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=False
        )
        return consumer_tag

    def ack(self, message: Message) -> None:
        if hasattr(message, '_channel') and hasattr(message, '_delivery_tag'):
            message._channel.basic_ack(message._delivery_tag)

    def nack(self, message: Message, requeue: bool = True) -> None:
        if hasattr(message, '_channel') and hasattr(message, '_delivery_tag'):
            message._channel.basic_nack(message._delivery_tag, requeue=requeue)

    def declare_queue(self, name: str, **options) -> None:
        arguments = {}

        if options.get('dead_letter_queue'):
            arguments['x-dead-letter-exchange'] = ''
            arguments['x-dead-letter-routing-key'] = options['dead_letter_queue']

        if options.get('ttl'):
            arguments['x-message-ttl'] = options['ttl']

        self.channel.queue_declare(
            queue=name,
            durable=options.get('durable', True),
            exclusive=options.get('exclusive', False),
            auto_delete=options.get('auto_delete', False),
            arguments=arguments or None
        )

    def declare_exchange(self, name: str, type: str, **options) -> None:
        self.channel.exchange_declare(
            exchange=name,
            exchange_type=type,
            durable=options.get('durable', True),
            auto_delete=options.get('auto_delete', False)
        )
```

### AWS SQS Adapter

```python
# src/runtime/adapters/sqs_adapter.py

import boto3
import json
from .message_broker import MessageBroker, Message

class SQSAdapter(MessageBroker):
    def __init__(self):
        self.sqs = None
        self.sns = None
        self.queues = {}
        self.topics = {}

    def connect(self, config: Dict[str, Any]) -> None:
        self.sqs = boto3.client(
            'sqs',
            region_name=config.get('region', 'us-east-1'),
            aws_access_key_id=config.get('access_key'),
            aws_secret_access_key=config.get('secret_key')
        )
        self.sns = boto3.client(
            'sns',
            region_name=config.get('region', 'us-east-1'),
            aws_access_key_id=config.get('access_key'),
            aws_secret_access_key=config.get('secret_key')
        )

    def publish(self, topic: str, message: Message) -> None:
        topic_arn = self._get_topic_arn(topic)

        self.sns.publish(
            TopicArn=topic_arn,
            Message=json.dumps(message.body),
            MessageAttributes={
                k: {'DataType': 'String', 'StringValue': v}
                for k, v in (message.headers or {}).items()
            }
        )

    def send(self, queue: str, message: Message) -> None:
        queue_url = self._get_queue_url(queue)

        self.sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message.body),
            MessageAttributes={
                k: {'DataType': 'String', 'StringValue': v}
                for k, v in (message.headers or {}).items()
            }
        )

    def consume(self, queue: str, handler: Callable[[Message], None]) -> str:
        queue_url = self._get_queue_url(queue)

        # Start polling in background
        import threading

        def poll():
            while True:
                response = self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20
                )

                for msg in response.get('Messages', []):
                    message = Message(
                        id=msg['MessageId'],
                        queue=queue,
                        body=json.loads(msg['Body']),
                        headers={
                            k: v['StringValue']
                            for k, v in msg.get('MessageAttributes', {}).items()
                        }
                    )
                    message._receipt_handle = msg['ReceiptHandle']
                    message._queue_url = queue_url
                    handler(message)

        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
        return str(thread.ident)

    def ack(self, message: Message) -> None:
        if hasattr(message, '_receipt_handle') and hasattr(message, '_queue_url'):
            self.sqs.delete_message(
                QueueUrl=message._queue_url,
                ReceiptHandle=message._receipt_handle
            )

    def _get_queue_url(self, queue: str) -> str:
        if queue not in self.queues:
            try:
                response = self.sqs.get_queue_url(QueueName=queue)
                self.queues[queue] = response['QueueUrl']
            except:
                response = self.sqs.create_queue(QueueName=queue)
                self.queues[queue] = response['QueueUrl']
        return self.queues[queue]

    def _get_topic_arn(self, topic: str) -> str:
        if topic not in self.topics:
            response = self.sns.create_topic(Name=topic.replace('.', '-'))
            self.topics[topic] = response['TopicArn']
        return self.topics[topic]
```

### Redis Pub/Sub Adapter

```python
# src/runtime/adapters/redis_adapter.py

import redis
import json
from .message_broker import MessageBroker, Message

class RedisAdapter(MessageBroker):
    def __init__(self):
        self.redis = None
        self.pubsub = None

    def connect(self, config: Dict[str, Any]) -> None:
        self.redis = redis.Redis(
            host=config.get('host', 'localhost'),
            port=config.get('port', 6379),
            db=config.get('db', 0),
            password=config.get('password')
        )
        self.pubsub = self.redis.pubsub()

    def publish(self, topic: str, message: Message) -> None:
        data = {
            'id': message.id,
            'body': message.body,
            'headers': message.headers,
            'timestamp': message.timestamp
        }
        self.redis.publish(topic, json.dumps(data))

    def send(self, queue: str, message: Message) -> None:
        data = {
            'id': message.id,
            'body': message.body,
            'headers': message.headers,
            'timestamp': message.timestamp
        }
        self.redis.lpush(f'queue:{queue}', json.dumps(data))

    def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        def message_handler(msg):
            if msg['type'] == 'message':
                data = json.loads(msg['data'])
                message = Message(
                    id=data['id'],
                    topic=msg['channel'].decode(),
                    body=data['body'],
                    headers=data.get('headers')
                )
                handler(message)

        self.pubsub.psubscribe(**{topic: message_handler})

        import threading
        thread = threading.Thread(target=self.pubsub.run_in_thread, daemon=True)
        thread.start()
        return str(thread.ident)

    def consume(self, queue: str, handler: Callable[[Message], None]) -> str:
        import threading

        def poll():
            while True:
                result = self.redis.brpop(f'queue:{queue}', timeout=1)
                if result:
                    data = json.loads(result[1])
                    message = Message(
                        id=data['id'],
                        queue=queue,
                        body=data['body'],
                        headers=data.get('headers')
                    )
                    handler(message)

        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
        return str(thread.ident)

    def ack(self, message: Message) -> None:
        # Redis queues are auto-acked on pop
        pass
```

## Configuracao

### quantum.yaml

```yaml
message_broker:
  # Escolher um: rabbitmq, sqs, redis
  type: rabbitmq

  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
    vhost: /

  sqs:
    region: us-east-1
    access_key: ${AWS_ACCESS_KEY}
    secret_key: ${AWS_SECRET_KEY}

  redis:
    host: localhost
    port: 6379
    db: 0
    password: ${REDIS_PASSWORD}
```

## Exemplos de Uso

### 1. Event-Driven Order Processing

```xml
<!-- order-service.q -->
<q:component name="OrderService">
    <!-- Quando um pedido e criado -->
    <q:action name="createOrder">
        <q:query name="order" datasource="db">
            INSERT INTO orders (customer_id, items, total)
            VALUES (:customerId, :items, :total)
        </q:query>

        <!-- Publicar evento -->
        <q:message topic="orders.created" type="publish">
            <q:body>
                {
                    "orderId": {order.insertId},
                    "customerId": {customerId},
                    "items": {items},
                    "total": {total}
                }
            </q:body>
        </q:message>

        <q:return value="{order.insertId}" />
    </q:action>
</q:component>

<!-- payment-service.q -->
<q:component name="PaymentService">
    <q:subscribe topic="orders.created" name="payment-handler">
        <q:on-message>
            <q:invoke name="payment"
                      url="https://payment.api/charge"
                      method="POST">
                <q:body>
                    {
                        "orderId": {message.body.orderId},
                        "amount": {message.body.total}
                    }
                </q:body>
            </q:invoke>

            <q:if condition="{payment.success}">
                <q:message topic="payments.completed" type="publish">
                    <q:body>
                        {
                            "orderId": {message.body.orderId},
                            "transactionId": {payment.transactionId}
                        }
                    </q:body>
                </q:message>
            </q:if>
            <q:else>
                <q:message topic="payments.failed" type="publish">
                    <q:body>
                        {
                            "orderId": {message.body.orderId},
                            "error": {payment.error}
                        }
                    </q:body>
                </q:message>
            </q:else>
        </q:on-message>
    </q:subscribe>
</q:component>

<!-- notification-service.q -->
<q:component name="NotificationService">
    <q:subscribe topics="orders.*, payments.*" name="notification-handler">
        <q:on-message>
            <q:query name="customer" datasource="db">
                SELECT email FROM customers WHERE id = :customerId
                <q:param name="customerId" value="{message.body.customerId}" />
            </q:query>

            <q:if condition="{message.topic == 'payments.completed'}">
                <q:mail to="{customer.email}" subject="Payment Confirmed!">
                    <q:body>
                        Your payment for order #{message.body.orderId} was successful!
                    </q:body>
                </q:mail>
            </q:if>
        </q:on-message>
    </q:subscribe>
</q:component>
```

### 2. Work Queue para Processamento Pesado

```xml
<!-- image-processor.q -->
<q:component name="ImageProcessor">
    <!-- Enfileirar imagem para processamento -->
    <q:action name="uploadImage">
        <q:file name="image" destination="uploads/" />

        <q:message queue="image-processing" type="send">
            <q:body>
                {
                    "imagePath": {image.path},
                    "userId": {session.userId},
                    "operations": ["resize", "optimize", "watermark"]
                }
            </q:body>
        </q:message>

        <p>Image queued for processing!</p>
    </q:action>

    <!-- Worker que processa as imagens -->
    <q:subscribe queue="image-processing"
                 name="image-worker"
                 prefetch="1">
        <q:on-message>
            <q:loop type="array" var="op" items="{message.body.operations}">
                <q:invoke function="processImage">
                    <q:arg name="path" value="{message.body.imagePath}" />
                    <q:arg name="operation" value="{op}" />
                </q:invoke>
            </q:loop>

            <!-- Notificar usuario -->
            <q:message topic="images.processed" type="publish">
                <q:body>
                    {
                        "userId": {message.body.userId},
                        "imagePath": {message.body.imagePath}
                    }
                </q:body>
            </q:message>

            <q:message-ack />
        </q:on-message>

        <q:on-error>
            <q:log level="error">Image processing failed: {error.message}</q:log>

            <!-- Enviar para DLQ apos 3 tentativas -->
            <q:if condition="{message.headers.retry-count >= 3}">
                <q:message queue="image-processing.dlq" type="send">
                    <q:body>{message}</q:body>
                </q:message>
                <q:message-ack />
            </q:if>
            <q:else>
                <q:message-nack requeue="true" />
            </q:else>
        </q:on-error>
    </q:subscribe>
</q:component>
```

### 3. Request-Reply Pattern

```xml
<!-- calculator-service.q -->
<q:component name="CalculatorService">
    <!-- Servidor -->
    <q:subscribe queue="calculations" name="calc-worker">
        <q:on-message>
            <q:set name="numbers" value="{message.body.numbers}" />
            <q:set name="result" value="0" />

            <q:loop type="array" var="num" items="{numbers}">
                <q:set name="result" operation="add" value="{num}" />
            </q:loop>

            <!-- Responder na reply queue -->
            <q:message queue="{message.headers.reply-to}" type="send">
                <q:header name="correlation-id" value="{message.headers.correlation-id}" />
                <q:body>{"result": {result}}</q:body>
            </q:message>

            <q:message-ack />
        </q:on-message>
    </q:subscribe>
</q:component>

<!-- client.q -->
<q:component name="CalculatorClient">
    <q:action name="calculateSum">
        <!-- Request-Reply com timeout -->
        <q:message name="response"
                   queue="calculations"
                   type="request"
                   timeout="10s">
            <q:body>{"numbers": [1, 2, 3, 4, 5]}</q:body>
        </q:message>

        <p>The sum is: {response.result}</p>
    </q:action>
</q:component>
```

### 4. Saga Pattern para Transacoes Distribuidas

```xml
<!-- saga-orchestrator.q -->
<q:component name="OrderSaga">
    <q:action name="startOrderSaga">
        <q:set name="sagaId" value="{uuid()}" />

        <!-- Step 1: Reserve inventory -->
        <q:message queue="inventory.reserve" type="send">
            <q:header name="saga-id" value="{sagaId}" />
            <q:body>{"items": {order.items}}</q:body>
        </q:message>
    </q:action>

    <!-- Handle inventory reserved -->
    <q:subscribe topic="inventory.reserved" name="saga-inventory">
        <q:on-message>
            <!-- Step 2: Process payment -->
            <q:message queue="payments.process" type="send">
                <q:header name="saga-id" value="{message.headers.saga-id}" />
                <q:body>{"amount": {message.body.total}}</q:body>
            </q:message>
        </q:on-message>
    </q:subscribe>

    <!-- Handle payment completed -->
    <q:subscribe topic="payments.completed" name="saga-payment">
        <q:on-message>
            <!-- Step 3: Confirm order -->
            <q:message topic="orders.confirmed" type="publish">
                <q:body>{"sagaId": "{message.headers.saga-id}"}</q:body>
            </q:message>
        </q:on-message>
    </q:subscribe>

    <!-- Handle failures - compensating transactions -->
    <q:subscribe topic="payments.failed" name="saga-compensation">
        <q:on-message>
            <!-- Rollback: Release inventory -->
            <q:message queue="inventory.release" type="send">
                <q:header name="saga-id" value="{message.headers.saga-id}" />
                <q:body>{}</q:body>
            </q:message>

            <!-- Notify order failed -->
            <q:message topic="orders.failed" type="publish">
                <q:body>
                    {
                        "sagaId": "{message.headers.saga-id}",
                        "reason": "Payment failed"
                    }
                </q:body>
            </q:message>
        </q:on-message>
    </q:subscribe>
</q:component>
```

## CLI Integration

```bash
# Listar queues
quantum mq queues list

# Ver mensagens em uma queue (peek)
quantum mq queues peek orders --limit 10

# Purge queue
quantum mq queues purge test-queue

# Publicar mensagem
quantum mq publish orders.created '{"orderId": 123}'

# Consumir mensagens (debug)
quantum mq consume orders --limit 1

# Worker mode
quantum mq worker --queues "orders,payments" --concurrency 4

# Stats
quantum mq stats
```

## Cronograma de Implementacao

### Fase 1: Core Infrastructure (1 semana)
- [ ] MessageBroker abstraction
- [ ] AST nodes (MessageNode, SubscribeNode, QueueNode)
- [ ] Parser implementation
- [ ] Redis adapter (mais simples para comecar)

### Fase 2: RabbitMQ Support (1 semana)
- [ ] RabbitMQ adapter
- [ ] Exchange e routing
- [ ] Acknowledgments
- [ ] Dead letter queues

### Fase 3: AWS SQS Support (1 semana)
- [ ] SQS adapter
- [ ] SNS integration para pub/sub
- [ ] FIFO queues
- [ ] Visibility timeout

### Fase 4: Advanced Features (1 semana)
- [ ] Request-reply pattern
- [ ] Message batching
- [ ] Priority queues
- [ ] CLI commands
- [ ] Monitoring/metrics

### Fase 5: Documentation (3 dias)
- [ ] User guide
- [ ] Examples
- [ ] Best practices

## Dependencias

```python
# requirements.txt
pika>=1.3.0           # RabbitMQ
boto3>=1.28.0         # AWS SQS/SNS
redis>=4.0.0          # Redis
```

## Metricas de Sucesso

- [ ] 3 adapters implementados (Redis, RabbitMQ, SQS)
- [ ] Pub/sub funcionando
- [ ] Work queues funcionando
- [ ] Request-reply pattern funcionando
- [ ] CLI commands implementados
- [ ] 10+ exemplos praticos
- [ ] Documentacao completa
- [ ] Testes de integracao
