#!/usr/bin/env python3
"""
Generate FastAPI + Dapr + AI Agent Microservice

Usage: python generate_service.py <service-name> --port 8080
"""

import argparse
import sys
from pathlib import Path


def create_main_py(service_name: str, port: int) -> str:
    """Create main FastAPI application."""
    service_title = service_name.replace('-', ' ').title()
    
    return f'''#!/usr/bin/env python3
"""
{service_title} Service

A FastAPI microservice with Dapr integration and AI agent capabilities.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Dapr sidecar configuration
DAPR_HTTP_PORT = os.getenv("DAPR_HTTP_PORT", "3500")
DAPR_GRPC_PORT = os.getenv("DAPR_GRPC_PORT", "50001")
SERVICE_NAME = "{service_name}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {{SERVICE_NAME}} service...")
    
    # Initialize connections
    yield
    
    # Cleanup
    logger.info(f"Shutting down {{SERVICE_NAME}} service...")


app = FastAPI(
    title="{service_title}",
    description="Microservice with Dapr integration and AI capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class MessageRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    response: str
    success: bool


# ============== Health Endpoints ==============

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version="1.0.0"
    )


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint."""
    # Check Dapr connectivity
    try:
        resp = requests.get(f"http://localhost:{{DAPR_HTTP_PORT}}/v1.0/healthz", timeout=5)
        if resp.status_code == 200:
            return {{"status": "ready", "dapr": "connected"}}
    except Exception as e:
        logger.warning(f"Dapr not ready: {{e}}")
    
    return {{"status": "not ready", "dapr": "disconnected"}}


# ============== Dapr Pub/Sub Endpoints ==============

@app.post("/publish/{{{{topic}}}}", tags=["Pub/Sub"])
async def publish_event(topic: str, data: Dict[str, Any]):
    """Publish event to Dapr pub/sub."""
    try:
        resp = requests.post(
            f"http://localhost:{{DAPR_HTTP_PORT}}/v1.0/publish/{{{{topic}}}}",
            json=data,
            timeout=5
        )
        if resp.status_code == 200:
            return {{"success": True, "topic": topic}}
        else:
            raise HTTPException(status_code=500, detail="Failed to publish event")
    except Exception as e:
        logger.error(f"Publish failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/subscribe/{{{{topic}}}}")
async def subscribe_event(topic: str, data: Dict[str, Any]):
    """Subscribe to events from Dapr pub/sub."""
    logger.info(f"Received event from {{topic}}: {{data}}")
    
    # Process the event
    # TODO: Implement your event handling logic here
    
    return {{"success": True}}


# ============== Dapr State Management ==============

@app.get("/state/{{{{key}}}}", tags=["State"])
async def get_state(key: str, store_name: str = "{service_name}-state"):
    """Get state from Dapr state store."""
    try:
        resp = requests.get(
            f"http://localhost:{{DAPR_HTTP_PORT}}/v1.0/state/{{{{store_name}}}}/{{{{key}}}}",
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            raise HTTPException(status_code=404, detail="Key not found")
    except Exception as e:
        logger.error(f"Get state failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/state", tags=["State"])
async def save_state(key: str, value: Dict[str, Any], store_name: str = "{service_name}-state"):
    """Save state to Dapr state store."""
    try:
        resp = requests.post(
            f"http://localhost:{{DAPR_HTTP_PORT}}/v1.0/state/{{{{store_name}}}}",
            json=[{{"key": key, "value": value}}],
            timeout=5
        )
        if resp.status_code == 200:
            return {{"success": True, "key": key}}
        else:
            raise HTTPException(status_code=500, detail="Failed to save state")
    except Exception as e:
        logger.error(f"Save state failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== AI Agent Integration ==============

class AIRequest(BaseModel):
    prompt: str
    system_message: Optional[str] = "You are a helpful AI assistant."
    max_tokens: Optional[int] = 2048


class AIResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict[str, int]] = None


@app.post("/ai/chat", response_model=AIResponse, tags=["AI"])
async def ai_chat(request: AIRequest):
    """Send request to AI model."""
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")  # For Claude Code Router or other proxies
        )
        
        response = client.chat.completions.create(
            model=os.getenv("AI_MODEL", "gpt-4o-mini"),
            messages=[
                {{"role": "system", "content": request.system_message}},
                {{"role": "user", "content": request.prompt}}
            ],
            max_tokens=request.max_tokens
        )
        
        return AIResponse(
            response=response.choices[0].message.content,
            model=response.model,
            usage={{"prompt_tokens": response.usage.prompt_tokens,
                   "completion_tokens": response.usage.completion_tokens,
                   "total_tokens": response.usage.total_tokens}}
            if response.usage else None
        )
        
    except ImportError:
        raise HTTPException(status_code=500, detail="OpenAI SDK not installed")
    except Exception as e:
        logger.error(f"AI request failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port={port},
        reload=True,
        log_level="info"
    )
'''


def create_requirements() -> str:
    """Create requirements.txt."""
    return """# FastAPI and server
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# HTTP client
requests==2.31.0
httpx==0.26.0

# AI integration
openai==1.10.0

# Dapr (optional - for advanced features)
# dapr==1.12.0
# dapr-ext-fastapi==1.12.0

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0

# Utilities
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
"""


def create_dockerfile(service_name: str, port: int) -> str:
    """Create Dockerfile."""
    return f'''# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application
COPY main.py .

# Add local bin to PATH
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:{port}/health')"

# Run application
CMD ["python", "main.py"]
'''


def create_dapr_yaml(service_name: str, port: int) -> str:
    """Create Dapr configuration."""
    return f'''apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: {service_name}-config
  namespace: default
spec:
  tracing:
    samplingRate: "1"
    zipkin:
      endpointAddress: "http://localhost:9411/api/v2/spans"
  metrics:
    enabled: true
---
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: {service_name}-pubsub
  namespace: default
spec:
  type: pubsub.kafka
  version: v1
  metadata:
  - name: brokers
    value: "kafka-headless.kafka:9092"
  - name: authType
    value: "none"
---
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: {service_name}-state
  namespace: default
spec:
  type: state.redis
  version: v1
  metadata:
  - name: redisHost
    value: "localhost:6379"
  - name: redisPassword
    value: ""
  - name: actorStateStore
    value: "true"
'''


def create_k8s_deployment(service_name: str, port: int) -> str:
    """Create Kubernetes deployment."""
    return f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service_name}
  labels:
    app: {service_name}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {service_name}
  template:
    metadata:
      labels:
        app: {service_name}
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "{service_name}"
        dapr.io/app-port: "{port}"
        dapr.io/config: "{service_name}-config"
    spec:
      containers:
      - name: {service_name}
        image: {service_name}:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
        env:
        - name: DAPR_HTTP_PORT
          value: "3500"
        - name: DAPR_GRPC_PORT
          value: "50001"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-api-key
              optional: true
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  labels:
    app: {service_name}
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: {port}
    protocol: TCP
    name: http
  selector:
    app: {service_name}
'''


def create_test_file(service_name: str) -> str:
    """Create test file."""
    return f'''#!/usr/bin/env python3
"""Tests for {service_name} service."""

import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_health_check():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "{service_name}"


def test_readiness_check():
    """Test readiness endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200


def test_ai_chat():
    """Test AI chat endpoint (mocked)."""
    # This would require mocking the OpenAI client
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''


def create_readme(service_name: str, port: int) -> str:
    """Create README."""
    service_title = service_name.replace('-', ' ').title()
    
    return f'''# {service_title} Service

FastAPI microservice with Dapr integration and AI capabilities.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Dapr
dapr run --app-id {service_name} --app-port {port} --dapr-http-port 3500 \\
  python main.py
```

### Docker

```bash
# Build
docker build -t {service_name}:latest .

# Run
docker run -p {port}:{port} {service_name}:latest
```

### Kubernetes

```bash
# Deploy
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods -l app={service_name}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/publish/{{{{topic}}}}` | POST | Publish event |
| `/state/{{{{key}}}}` | GET | Get state |
| `/state` | POST | Save state |
| `/ai/chat` | POST | AI chat |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DAPR_HTTP_PORT` | 3500 | Dapr HTTP port |
| `DAPR_GRPC_PORT` | 50001 | Dapr gRPC port |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `AI_MODEL` | gpt-4o-mini | AI model to use |

## Testing

```bash
pytest tests/ -v
```
'''


def generate_service(service_name: str, port: int) -> bool:
    """Generate complete service structure."""
    base_dir = Path(service_name)
    
    # Create directories
    (base_dir / "k8s").mkdir(parents=True, exist_ok=True)
    (base_dir / "tests").mkdir(parents=True, exist_ok=True)
    
    # Generate files
    files = {
        base_dir / "main.py": create_main_py(service_name, port),
        base_dir / "requirements.txt": create_requirements(),
        base_dir / "Dockerfile": create_dockerfile(service_name, port),
        base_dir / "dapr.yaml": create_dapr_yaml(service_name, port),
        base_dir / "k8s" / "deployment.yaml": create_k8s_deployment(service_name, port),
        base_dir / "tests" / "test_main.py": create_test_file(service_name),
        base_dir / "README.md": create_readme(service_name, port),
    }
    
    for path, content in files.items():
        with open(path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created {path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate FastAPI + Dapr + AI Agent microservice"
    )
    parser.add_argument("name", help="Service name (e.g., triage-service)")
    parser.add_argument("-p", "--port", type=int, default=8080,
                       help="Service port (default: 8080)")
    
    args = parser.parse_args()
    
    print(f"Generating {args.name} service...")
    print("=" * 50)
    
    if generate_service(args.name, args.port):
        print("\n" + "=" * 50)
        print(f"✓ Service '{args.name}' generated successfully!")
        print(f"\nNext steps:")
        print(f"  cd {args.name}")
        print(f"  pip install -r requirements.txt")
        print(f"  dapr run --app-id {args.name} --app-port {args.port} python main.py")
        sys.exit(0)
    else:
        print("\n✗ Failed to generate service")
        sys.exit(1)


if __name__ == "__main__":
    main()
