---
name: k8s-foundation
description: Kubernetes cluster health checks and Helm operations
---

# Kubernetes Foundation Operations

## When to Use
- Checking cluster health before deployments
- Applying Helm charts to cluster
- Managing namespaces and resources
- Verifying cluster connectivity

## Instructions

### Check Cluster Health
1. Run health check: `python scripts/health_check.py`
2. Review cluster status output
3. Address any issues before proceeding

### Apply Helm Chart
1. Add repo: `python scripts/helm_ops.py add-repo <repo-name> <repo-url>`
2. Update repos: `python scripts/helm_ops.py update`
3. Install chart: `python scripts/helm_ops.py install <chart> <name> --namespace <ns>`
4. Verify: `python scripts/verify_installation.py <name> <namespace>`

### Manage Namespaces
1. Create: `python scripts/namespace_manager.py create <name>`
2. List: `python scripts/namespace_manager.py list`
3. Delete: `python scripts/namespace_manager.py delete <name>`

## Validation
- [ ] Cluster is healthy (all nodes Ready)
- [ ] Helm is configured
- [ ] Target namespace exists

## Troubleshooting
If cluster health fails:
1. Check Minikube status: `minikube status`
2. Check nodes: `kubectl get nodes`
3. Restart if needed: `minikube restart`

See [REFERENCE.md](./REFERENCE.md) for Helm chart configurations.
