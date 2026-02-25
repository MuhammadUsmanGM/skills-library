# Next.js Kubernetes Deployment Reference

## Quick Start

```bash
# Generate deployment files
python scripts/generate_deployment.py learnflow-frontend --port 3000

# Build image
python scripts/build_image.py learnflow-frontend --test

# Deploy to Kubernetes
python scripts/deploy.py learnflow-frontend --namespace apps

# Verify
python scripts/verify.py learnflow-frontend --namespace apps
```

## Next.js Configuration

### next.config.js for Kubernetes

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  distDir: '.next',
  
  // Environment variables
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  
  // Security headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
```

### Health Check API Route

```javascript
// app/api/health/route.js
export async function GET() {
  return Response.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
  })
}
```

## Dockerfile Patterns

### Multi-Stage Production Build

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
ENV NODE_ENV=production
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Security: non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

## Kubernetes Resources

### Deployment with Resource Limits

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: learnflow-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: learnflow-frontend
  template:
    metadata:
      labels:
        app: learnflow-frontend
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
      containers:
      - name: learnflow-frontend
        image: learnflow-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: NEXT_PUBLIC_API_URL
          value: "http://api.learnflow.local"
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
            port: 3000
          initialDelaySeconds: 15
          periodSeconds: 20
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: learnflow-frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: learnflow-frontend
  minReplicas: 2
  maxReplicas: 10
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
```

### Ingress with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: learnflow-frontend-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - learnflow.example.com
    secretName: learnflow-tls
  rules:
  - host: learnflow.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: learnflow-frontend
            port:
              number: 80
```

## Environment Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: learnflow-frontend-config
data:
  NEXT_PUBLIC_APP_NAME: "LearnFlow"
  NEXT_PUBLIC_ENV: "production"
  NEXT_PUBLIC_API_URL: "http://api.learnflow.local"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: learnflow-frontend-secrets
type: Opaque
stringData:
  NEXT_PUBLIC_ANALYTICS_ID: "UA-XXXXX-Y"
```

## Scaling Strategies

### Manual Scaling

```bash
kubectl scale deployment learnflow-frontend --replicas=5 -n apps
```

### Auto-Scaling (HPA)

```bash
# View HPA status
kubectl get hpa learnflow-frontend-hpa -n apps

# Edit HPA
kubectl edit hpa learnflow-frontend-hpa -n apps
```

### Cluster Autoscaling

Enable cluster autoscaler for node-level scaling:

```yaml
# Cluster Autoscaler configuration
--balance-similar-node-groups
--expander=least-waste
--max-node-provision-time=15m
```

## Monitoring

### Prometheus Annotations

```yaml
template:
  metadata:
    annotations:
      prometheus.io/scrape: "true"
      prometheus.io/port: "3000"
      prometheus.io/path: "/metrics"
```

### Custom Metrics

```javascript
// app/api/metrics/route.js
import { collectDefaultMetrics, register } from 'prom-client';

collectDefaultMetrics();

export async function GET() {
  const metrics = await register.metrics();
  return new Response(metrics, {
    headers: { 'Content-Type': register.contentType },
  });
}
```

## Security Best Practices

### Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: learnflow-frontend-network-policy
spec:
  podSelector:
    matchLabels:
      app: learnflow-frontend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: apps
    ports:
    - protocol: TCP
      port: 80
```

### Pod Security Context

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  fsGroup: 1001
  seccompProfile:
    type: RuntimeDefault

containers:
- name: app
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop:
      - ALL
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n apps

# Check logs
kubectl logs <pod-name> -n apps

# Check events
kubectl get events -n apps --sort-by='.lastTimestamp'
```

### Image Pull Errors

```bash
# For Minikube
minikube image load learnflow-frontend:latest

# For kind
kind load docker-image learnflow-frontend:latest
```

### Service Not Accessible

```bash
# Check endpoints
kubectl get endpoints learnflow-frontend -n apps

# Test from within cluster
kubectl run test --rm -it --image=curlimages/curl -- sh
curl http://learnflow-frontend.apps.svc.cluster.local/api/health
```

### High Memory Usage

```bash
# Check memory limits
kubectl top pods -n apps -l app=learnflow-frontend

# Adjust limits
kubectl edit deployment learnflow-frontend -n apps
```

## Performance Optimization

### Node.js Memory Tuning

```yaml
env:
- name: NODE_OPTIONS
  value: "--max-old-space-size=4096"
- name: NODE_ENV
  value: "production"
```

### Next.js Optimization

```javascript
// next.config.js
module.exports = {
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200],
  },
  experimental: {
    optimizePackageImports: ['@mui/material', 'lodash'],
  },
}
```

### CDN Configuration

```yaml
# Ingress with CDN
annotations:
  nginx.ingress.kubernetes.io/proxy-cache-path: "/var/cache/nginx"
  nginx.ingress.kubernetes.io/proxy-cache: "learnflow-cache"
  nginx.ingress.kubernetes.io/proxy-cache-valid: "200 10m"
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Build Docker image
      run: docker build -t learnflow-frontend:${{ github.sha }} .
    
    - name: Push to registry
      run: |
        docker tag learnflow-frontend:${{ github.sha }} registry.example.com/learnflow-frontend:${{ github.sha }}
        docker push registry.example.com/learnflow-frontend:${{ github.sha }}
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/learnflow-frontend \
          learnflow-frontend=registry.example.com/learnflow-frontend:${{ github.sha }} \
          -n apps
```

## Related Resources

- [Next.js Docker Documentation](https://nextjs.org/docs/deployment#docker-image)
- [Kubernetes Deployment Guide](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
