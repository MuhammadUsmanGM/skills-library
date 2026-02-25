---
name: fastapi-dapr-agent
description: Create FastAPI microservices with Dapr and AI agents
---

# FastAPI + Dapr + AI Agent Service Generator

## When to Use
- Building microservices for LearnFlow platform
- Need Dapr pub/sub for event-driven architecture
- Integrating AI agents (OpenAI SDK) into services
- Creating REST APIs with automatic documentation

## Instructions

### Generate New Service
1. Run generator: `python scripts/generate_service.py <service-name> --port 8080`
2. Review generated files
3. Install dependencies: `pip install -r requirements.txt`

### Run Service with Dapr
1. Start with Dapr: `python scripts/run_with_dapr.py <service-name> --port 8080`
2. Test endpoints: `curl http://localhost:8080/health`
3. Check Dapr dashboard: `dapr dashboard -p 8081`

### Deploy to Kubernetes
1. Run deploy: `python scripts/deploy.py <service-name> --namespace apps`
2. Verify: `kubectl get pods -n apps`
3. Test: `kubectl port-forward svc/<service-name> -n apps 8080:80`

## Generated Structure

```
<service-name>/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build
├── dapr.yaml           # Dapr configuration
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── dapr-component.yaml
└── tests/
    └── test_main.py
```

## Validation
- [ ] Service starts without errors
- [ ] Health endpoint returns 200
- [ ] Dapr sidecar attached
- [ ] Can publish/subscribe to events

See [REFERENCE.md](./REFERENCE.md) for Dapr patterns and AI integration.
