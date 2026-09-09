# RabbitMQ Examples

This directory contains examples demonstrating RabbitMQ integration with Quantum.

## Prerequisites

### 1. Install RabbitMQ

**Windows (via Chocolatey):**
```powershell
choco install rabbitmq
```

**Windows (via Scoop):**
```powershell
scoop install rabbitmq
```

**Docker (recommended for development):**
```bash
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management
```

### 2. Access Management UI

Open http://localhost:15672 in your browser.
- Username: `guest`
- Password: `guest`

### 3. Install Python Client

```bash
pip install pika
```

## Examples

| File | Description |
|------|-------------|
| `01_hello_world.py` | Simple producer/consumer |
| `02_work_queue.py` | Task distribution with workers |
| `03_pubsub.py` | Fanout exchange (broadcast) |
| `04_topics.py` | Topic-based routing |
| `05_rpc.py` | Request/Reply pattern |
| `order_system.q` | Full order processing system |

## Running the Examples

### Python Examples

```bash
# Terminal 1: Start consumer
python examples/rabbitmq/01_hello_world.py receive

# Terminal 2: Send message
python examples/rabbitmq/01_hello_world.py send "Hello World!"
```

### Quantum Examples

```bash
# Set environment variable
set MESSAGE_BROKER_TYPE=rabbitmq

# Run Quantum component
python src/cli/runner.py run examples/rabbitmq/order_system.q
```

## Environment Variables

```bash
# Broker type
MESSAGE_BROKER_TYPE=rabbitmq

# Connection settings
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
```
