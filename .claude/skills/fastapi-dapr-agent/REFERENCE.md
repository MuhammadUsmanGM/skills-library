# FastAPI + Dapr + AI Agent Reference

## Quick Start

```bash
# Generate new service
python scripts/generate_service.py triage-service --port 8080

# Run locally with Dapr
cd triage-service
dapr run --app-id triage-service --app-port 8080 --dapr-http-port 3500 \
  python main.py

# Test health endpoint
curl http://localhost:8080/health

# Deploy to Kubernetes
python scripts/deploy.py triage-service --namespace apps
```

## LearnFlow Services

Generate these services for the complete LearnFlow platform:

```bash
# Triage Service - Routes requests to appropriate agents
python scripts/generate_service.py triage-service --port 8081

# Concepts Service - Explains Python concepts
python scripts/generate_service.py concepts-service --port 8082

# Code Review Service - Analyzes code submissions
python scripts/generate_service.py code-review-service --port 8083

# Debug Service - Helps debug errors
python scripts/generate_service.py debug-service --port 8084

# Exercise Service - Generates and grades exercises
python scripts/generate_service.py exercise-service --port 8085

# Progress Service - Tracks student progress
python scripts/generate_service.py progress-service --port 8086
```

## Dapr Building Blocks

### Pub/Sub Messaging

```python
# Publish event
import requests

DAPR_HTTP_PORT = "3500"

requests.post(
    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish/learning.events",
    json={
        "event_type": "exercise_completed",
        "user_id": "123",
        "score": 85
    }
)

# Subscribe to events (in your FastAPI app)
@app.post("/subscribe/learning.events")
async def handle_learning_event(data: dict):
    logger.info(f"Received event: {data}")
    return {"success": True}
```

### State Management

```python
# Save state
requests.post(
    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{service_name}-state",
    json=[{
        "key": "user:123:progress",
        "value": {"module": "loops", "score": 85}
    }]
)

# Get state
resp = requests.get(
    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{service_name}-state/user:123:progress"
)
progress = resp.json()

# Delete state
requests.delete(
    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{service_name}-state/user:123:progress"
)
```

### Service Invocation

```python
# Call another service via Dapr
resp = requests.post(
    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/invoke/concepts-service/method/ai/chat",
    json={
        "prompt": "Explain for loops",
        "system_message": "You are a Python tutor"
    }
)
response = resp.json()
```

### Bindings (External Services)

```python
# Invoke output binding
requests.post(
    f"http://localhost:{DAPR_HTTP_PORT}/v1.0/bindings/kafka-output",
    json={
        "operation": "create",
        "data": {"message": "Hello Kafka"},
        "metadata": {"topic": "learning.events"}
    }
)
```

## AI Agent Integration

### OpenAI SDK

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")  # Optional: for proxies
)

response = client.chat.completions.create(
    model=os.getenv("AI_MODEL", "gpt-4o-mini"),
    messages=[
        {"role": "system", "content": "You are a Python tutor."},
        {"role": "user", "content": "Explain list comprehensions"}
    ],
    max_tokens=1024
)

print(response.choices[0].message.content)
```

### Claude Code Router

```python
# Use Claude Code Router for model switching
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("CLAUDE_ROUTER_KEY"),
    base_url="https://router.claude.ai/v1"  # Example URL
)

# Router will select best model based on request
response = client.chat.completions.create(
    model="auto",  # Let router decide
    messages=[{"role": "user", "content": "Explain Python decorators"}]
)
```

### Prompt Templates for Tutoring

```python
CONCEPT_EXPLANATION_PROMPT = """
You are a friendly Python tutor. Explain the concept of {concept} to a {level} student.

Include:
1. A simple definition
2. A practical example
3. Common mistakes to avoid
4. A practice exercise

Keep the explanation under 200 words.
"""

CODE_REVIEW_PROMPT = """
Review this Python code and provide constructive feedback:

```python
{code}
```

Evaluate:
1. Correctness - Does it work?
2. Style - PEP 8 compliance
3. Efficiency - Can it be optimized?
4. Readability - Is it clear?

Provide specific suggestions for improvement.
"""

DEBUG_HELP_PROMPT = """
Help me understand and fix this error:

Error: {error_message}
Code: {code}

Don't give the solution directly. Instead:
1. Explain what the error means
2. Point to the likely cause
3. Give a hint about how to fix it
"""
```

## Kubernetes Deployment

### Service Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: triage-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: triage-service
  template:
    metadata:
      labels:
        app: triage-service
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "triage-service"
        dapr.io/app-port: "8080"
        dapr.io/config: "triage-service-config"
    spec:
      containers:
      - name: triage-service
        image: triage-service:latest
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-api-key
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

### Dapr Configuration

```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: triage-service-config
spec:
  tracing:
    samplingRate: "1"
  metrics:
    enabled: true
  secrets:
    scopes:
    - storeName: kubernetes-secrets
      defaultAccess: allow
```

### Kafka Pub/Sub Component

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: triage-service-pubsub
spec:
  type: pubsub.kafka
  version: v1
  metadata:
  - name: brokers
    value: "kafka-headless.kafka:9092"
  - name: authType
    value: "none"
  - name: consumerGroup
    value: "triage-service"
  - name: publishTopic
    value: "learning.events"
```

## Testing

### Unit Tests

```python
# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("main.OpenAI")
def test_ai_chat(mock_openai):
    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30
    
    mock_client.chat.completions.create.return_value = mock_response
    
    response = client.post("/ai/chat", json={
        "prompt": "Test prompt",
        "system_message": "Test system"
    })
    
    assert response.status_code == 200
    assert "response" in response.json()
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
import requests
import time

DAPR_HTTP_PORT = "3500"
SERVICE_URL = "http://localhost:8080"

def test_pubsub_integration():
    # Publish event
    resp = requests.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0/publish/test.topic",
        json={"test": "data"}
    )
    assert resp.status_code == 200

def test_state_integration():
    # Save state
    requests.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/test-state",
        json=[{"key": "test", "value": {"data": "value"}}]
    )
    
    # Get state
    resp = requests.get(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/test-state/test"
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == "value"
```

## Troubleshooting

### Dapr Sidecar Not Starting

```bash
# Check Dapr installation
dapr --version

# Initialize Dapr
dapr init

# For Kubernetes
dapr init --kubernetes

# Check Dapr pods
kubectl get pods -n dapr-system
```

### Service Cannot Connect to Dapr

```bash
# Verify app-id matches
kubectl get pods -l app=your-service -o jsonpath='{.items[0].metadata.annotations}'

# Check Dapr HTTP port
echo $DAPR_HTTP_PORT  # Should be 3500

# Test Dapr health
curl http://localhost:3500/v1.0/healthz
```

### AI Integration Fails

```bash
# Check environment variables
env | grep OPENAI

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Kubernetes Deployment Issues

```bash
# Check pod status
kubectl get pods -n apps

# Describe problematic pod
kubectl describe pod <pod-name> -n apps

# Check logs
kubectl logs <pod-name> -n apps
kubectl logs <pod-name> -c daprd -n apps  # Dapr sidecar logs

# Check events
kubectl get events -n apps --sort-by='.lastTimestamp'
```

## Performance Tuning

### Uvicorn Configuration

```python
# For production
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 4 \
  --loop uvloop \
  --http httptools
```

### Connection Pooling

```python
import httpx

# Create client with connection pool
client = httpx.AsyncClient(
    base_url="http://localhost:3500",
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)
```

### Caching

```python
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def get_cached_response(prompt_hash: str, response: str, ttl: int):
    return response

def cache_with_ttl(key: str, value: dict, ttl_seconds: int = 300):
    """Cache with time-to-live using Dapr state."""
    import requests
    
    requests.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0/state/{service_name}-state",
        json=[{
            "key": f"cache:{key}",
            "value": {
                "data": value,
                "expires_at": time.time() + ttl_seconds
            }
        }]
    )
```

## Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Dapr Documentation](https://docs.dapr.io/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Dapr Python SDK](https://github.com/dapr/python-sdk)
