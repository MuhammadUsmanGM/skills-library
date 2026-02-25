# Kubernetes Foundation Reference

## Common Helm Charts

### Apache Kafka (Bitnami)

```bash
# Add repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install Kafka (development configuration)
helm install kafka bitnami/kafka \
  --namespace kafka \
  --create-namespace \
  --set replicaCount=1 \
  --set zookeeper.replicaCount=1 \
  --set persistence.enabled=false \
  --set zookeeper.persistence.enabled=false

# For production (with persistence)
helm install kafka bitnami/kafka \
  --namespace kafka \
  --set replicaCount=3 \
  --set zookeeper.replicaCount=3 \
  --set persistence.size=10Gi
```

### PostgreSQL (Bitnami)

```bash
# Install PostgreSQL
helm install postgresql bitnami/postgresql \
  --namespace database \
  --create-namespace \
  --set auth.postgresPassword=securepassword \
  --set auth.database=learnflow \
  --set primary.persistence.size=5Gi

# Get credentials
kubectl get secret --namespace database postgresql \
  -o jsonpath="{.data.postgres-password}" | base64 -d
```

### Redis (Bitnami)

```bash
# Install Redis
helm install redis bitnami/redis \
  --namespace cache \
  --create-namespace \
  --set architecture=standalone \
  --set auth.enabled=true \
  --set auth.password=redispassword
```

### Kong API Gateway

```bash
# Add Kong repository
helm repo add kong https://charts.konghq.com
helm repo update

# Install Kong
helm install kong kong/kong \
  --namespace kong \
  --create-namespace \
  --set ingressController.enabled=true \
  --set proxy.http.enabled=true \
  --set proxy.http.servicePort=80
```

### Dapr

```bash
# Install Dapr CLI
# macOS: brew install dapr/tap/dapr-cli
# Windows: winget install dapr-cli

# Initialize Dapr on Kubernetes
dapr init --kubernetes

# Or with Helm
helm repo add dapr https://dapr.github.io/helm-charts/
helm repo update
helm install dapr dapr/dapr \
  --namespace dapr-system \
  --create-namespace \
  --set global.ha.enabled=true
```

## Kubernetes Quick Reference

### Namespaces

```bash
# Create namespace
kubectl create namespace <name>

# List namespaces
kubectl get namespaces

# Delete namespace
kubectl delete namespace <name>
```

### Pods

```bash
# List pods
kubectl get pods -n <namespace>

# List pods with labels
kubectl get pods -n <namespace> --show-labels

# Get pod details
kubectl describe pod <pod-name> -n <namespace>

# Get pod logs
kubectl logs <pod-name> -n <namespace>

# Follow logs
kubectl logs -f <pod-name> -n <namespace>

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- <command>
```

### Services

```bash
# List services
kubectl get services -n <namespace>

# Get service details
kubectl describe service <service-name> -n <namespace>

# Port forward
kubectl port-forward service/<service-name> <local-port>:<service-port> -n <namespace>
```

### Deployments

```bash
# List deployments
kubectl get deployments -n <namespace>

# Scale deployment
kubectl scale deployment <name> -n <namespace> --replicas=3

# Restart deployment
kubectl rollout restart deployment <name> -n <namespace>

# View rollout status
kubectl rollout status deployment <name> -n <namespace>
```

### ConfigMaps and Secrets

```bash
# Create configmap from literal
kubectl create configmap <name> \
  --from-literal=key=value \
  -n <namespace>

# Create configmap from file
kubectl create configmap <name> \
  --from-file=config.yaml \
  -n <namespace>

# Create secret from literal
kubectl create secret generic <name> \
  --from-literal=username=admin \
  --from-literal=password=secret \
  -n <namespace>

# Get secret value (base64 encoded)
kubectl get secret <name> -n <namespace> -o jsonpath="{.data.password}"

# Decode secret
kubectl get secret <name> -n <namespace> -o jsonpath="{.data.password}" | base64 -d
```

### Debugging Commands

```bash
# Check cluster events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Check node status
kubectl get nodes -o wide

# Check resource usage
kubectl top pods -n <namespace>
kubectl top nodes

# Debug networking
kubectl run test-pod --rm -it --image=busybox -- sh
# Inside pod: nslookup <service-name>

# Check PVC status
kubectl get pvc -n <namespace>

# Describe problematic resource
kubectl describe <resource-type> <resource-name> -n <namespace>
```

## Resource Limits

### Example Pod with Resource Limits

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
  - name: app
    image: myapp:latest
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
```

## Health Check Patterns

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 20
  timeoutSeconds: 5
  failureThreshold: 3
```

## Common Issues and Solutions

### Issue: Pods stuck in Pending

```bash
# Check why
kubectl describe pod <pod-name> -n <namespace>

# Common causes:
# 1. Insufficient resources - check node capacity
kubectl top nodes

# 2. PVC issues - check storage class
kubectl get storageclass

# 3. Image pull errors - verify image name
kubectl get pod <pod-name> -o yaml | grep image:
```

### Issue: CrashLoopBackOff

```bash
# Check logs
kubectl logs <pod-name> -n <namespace> --previous

# Check events
kubectl describe pod <pod-name> -n <namespace>

# Common causes:
# 1. Application error - check logs
# 2. Missing config - check ConfigMaps/Secrets
# 3. Port conflicts - verify container ports
```

### Issue: Service not accessible

```bash
# Check service endpoints
kubectl get endpoints <service-name> -n <namespace>

# Check pod labels match selector
kubectl get pods -n <namespace> --show-labels
kubectl describe service <service-name> -n <namespace>

# Test connectivity
kubectl run test --rm -it --image=busybox -- wget -qO- <service-name>:<port>
```

## Best Practices

1. **Always use namespaces** - Isolate environments (dev, staging, prod)
2. **Set resource limits** - Prevent resource exhaustion
3. **Use Helm for deployments** - Consistent, repeatable installations
4. **Enable persistence** - For stateful workloads (databases, Kafka)
5. **Monitor health** - Use readiness and liveness probes
6. **Secure secrets** - Never commit secrets to version control
7. **Label resources** - Enable better organization and selection
