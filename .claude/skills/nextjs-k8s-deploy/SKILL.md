---
name: nextjs-k8s-deploy
description: Deploy Next.js applications to Kubernetes
---

# Next.js Kubernetes Deployment

## When to Use
- Deploying Next.js frontend to Kubernetes
- Building containerized Next.js apps
- Setting up production-ready deployments

## Instructions

### Generate Deployment Files
1. Run generator: `python scripts/generate_deployment.py <app-name> --port 3000`
2. Review generated Dockerfile and K8s manifests
3. Customize as needed

### Build and Deploy
1. Build image: `python scripts/build_image.py <app-name>`
2. Deploy: `python scripts/deploy.py <app-name> --namespace apps`
3. Verify: `python scripts/verify.py <app-name> --namespace apps`

### Configure Ingress
1. Create ingress: `python scripts/create_ingress.py <app-name> --domain app.example.com`
2. Apply: `kubectl apply -f <app-name>/k8s/ingress.yaml`

## Validation
- [ ] Docker image builds successfully
- [ ] Pod is Running
- [ ] Service accessible via port-forward
- [ ] Health check passes

See [REFERENCE.md](./REFERENCE.md) for Next.js optimization and ingress configuration.
