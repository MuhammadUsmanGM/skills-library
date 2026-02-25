#!/usr/bin/env python3
"""
Generate Next.js Kubernetes Deployment Files

Usage: python generate_deployment.py <app-name> --port 3000
"""

import argparse
import sys
from pathlib import Path


def create_dockerfile(app_name: str, port: int) -> str:
    """Create optimized Next.js Dockerfile."""
    return f'''# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Build Next.js
ENV NODE_ENV=production
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE {port}

ENV PORT={port}
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD node -e "require('http').get('http://localhost:${{PORT}}/api/health', (r) => {{process.exit(r.statusCode === 200 ? 0 : 1)}})"

CMD ["node", "server.js"]
'''


def create_dockerignore() -> str:
    """Create .dockerignore file."""
    return '''# Dependencies
node_modules
npm-debug.log
yarn-error.log

# Next.js
.next
out

# Testing
coverage
.nyc_output

# Environment
.env
.env.local
.env.*.local

# IDE
.idea
.vscode
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Git
.git
.gitignore

# Docker
Dockerfile
docker-compose*.yml
.dockerignore

# Documentation
*.md
docs
'''


def create_k8s_deployment(app_name: str, port: int) -> str:
    """Create Kubernetes deployment manifest."""
    return f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  labels:
    app: {app_name}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "{port}"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
      containers:
      - name: {app_name}
        image: {app_name}:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
          protocol: TCP
        env:
        - name: NODE_ENV
          value: "production"
        - name: PORT
          value: "{port}"
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /api/health
            port: {port}
          initialDelaySeconds: 15
          periodSeconds: 20
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/health
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}
  labels:
    app: {app_name}
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: {port}
    protocol: TCP
    name: http
  selector:
    app: {app_name}
'''


def create_hpa(app_name: str, min_replicas: int = 2, max_replicas: int = 10) -> str:
    """Create Horizontal Pod Autoscaler."""
    return f'''apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {app_name}-hpa
  labels:
    app: {app_name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {app_name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
'''


def create_ingress(app_name: str, domain: str = "app.example.com") -> str:
    """Create Ingress manifest."""
    return f'''apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}-ingress
  labels:
    app: {app_name}
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - {domain}
    secretName: {app_name}-tls
  rules:
  - host: {domain}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {app_name}
            port:
              number: 80
'''


def create_configmap(app_name: str) -> str:
    """Create ConfigMap for Next.js configuration."""
    return f'''apiVersion: v1
kind: ConfigMap
metadata:
  name: {app_name}-config
  labels:
    app: {app_name}
data:
  NEXT_PUBLIC_APP_NAME: "{app_name}"
  NEXT_PUBLIC_ENV: "production"
  # Add more configuration as needed
  # NEXT_PUBLIC_API_URL: "http://api.example.com"
'''


def create_network_policy(app_name: str) -> str:
    """Create NetworkPolicy for security."""
    return f'''apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {app_name}-network-policy
  labels:
    app: {app_name}
spec:
  podSelector:
    matchLabels:
      app: {app_name}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
'''


def create_readme(app_name: str, port: int) -> str:
    """Create README for deployment."""
    return f'''# {app_name.title()} - Kubernetes Deployment

Next.js application deployment files for Kubernetes.

## Files Generated

```
{app_name}/
├── Dockerfile           # Multi-stage optimized build
├── .dockerignore        # Exclude files from build
└── k8s/
    ├── deployment.yaml  # Deployment + Service
    ├── hpa.yaml         # Horizontal Pod Autoscaler
    ├── ingress.yaml     # Ingress with TLS
    ├── configmap.yaml   # Configuration
    └── networkpolicy.yaml  # Network security
```

## Quick Start

### Build Image

```bash
python scripts/build_image.py {app_name}
```

### Deploy to Kubernetes

```bash
python scripts/deploy.py {app_name} --namespace apps
```

### Verify Deployment

```bash
python scripts/verify.py {app_name} --namespace apps
```

### Port Forward (Local Testing)

```bash
kubectl port-forward svc/{app_name} -n apps {port}:80
```

### Access via Ingress

```bash
# Apply ingress
kubectl apply -f {app_name}/k8s/ingress.yaml

# Get external IP
kubectl get ingress {app_name}-ingress -n apps
```

## Configuration

### Environment Variables

Set in ConfigMap or as secrets:

```yaml
env:
- name: NEXT_PUBLIC_API_URL
  value: "http://api.example.com"
- name: NODE_ENV
  value: "production"
```

### Scaling

HPA is configured to scale between 2-10 pods based on:
- CPU utilization > 70%
- Memory utilization > 80%

### Health Checks

- Liveness: `/api/health` every 20s
- Readiness: `/api/health` every 10s

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app={app_name} -n apps
```

### View Logs

```bash
kubectl logs -l app={app_name} -n apps -f
```

### Debug Pod

```bash
kubectl run debug --rm -it --image=nicolaka/netshoot --namespace apps -- sh
```
'''


def generate_deployment(app_name: str, port: int, domain: str) -> bool:
    """Generate all deployment files."""
    base_dir = Path(app_name)
    k8s_dir = base_dir / "k8s"
    
    # Create directories
    base_dir.mkdir(exist_ok=True)
    k8s_dir.mkdir(exist_ok=True)
    
    # Generate files
    files = {
        base_dir / "Dockerfile": create_dockerfile(app_name, port),
        base_dir / ".dockerignore": create_dockerignore(),
        k8s_dir / "deployment.yaml": create_k8s_deployment(app_name, port),
        k8s_dir / "hpa.yaml": create_hpa(app_name),
        k8s_dir / "ingress.yaml": create_ingress(app_name, domain),
        k8s_dir / "configmap.yaml": create_configmap(app_name),
        k8s_dir / "networkpolicy.yaml": create_network_policy(app_name),
        base_dir / "README.md": create_readme(app_name, port),
    }
    
    for path, content in files.items():
        with open(path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created {path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate Next.js Kubernetes deployment files"
    )
    parser.add_argument("name", help="Application name (e.g., learnflow-frontend)")
    parser.add_argument("-p", "--port", type=int, default=3000,
                       help="Container port (default: 3000)")
    parser.add_argument("-d", "--domain", default="app.example.com",
                       help="Ingress domain (default: app.example.com)")
    
    args = parser.parse_args()
    
    print(f"Generating deployment files for {args.name}...")
    print("=" * 50)
    
    if generate_deployment(args.name, args.port, args.domain):
        print("\n" + "=" * 50)
        print(f"✓ Deployment files generated for {args.name}")
        print(f"\nNext steps:")
        print(f"  1. Review {args.name}/Dockerfile")
        print(f"  2. Update {args.name}/k8s/ingress.yaml with your domain")
        print(f"  3. Run: python scripts/build_image.py {args.name}")
        print(f"  4. Run: python scripts/deploy.py {args.name} --namespace apps")
        sys.exit(0)
    else:
        print("\n✗ Failed to generate deployment files")
        sys.exit(1)


if __name__ == "__main__":
    main()
