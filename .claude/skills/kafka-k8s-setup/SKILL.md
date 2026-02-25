---
name: kafka-k8s-setup
description: Deploy Apache Kafka on Kubernetes with Helm
---

# Kafka Kubernetes Setup

## When to Use
- User asks to deploy Kafka for event-driven architecture
- Setting up message broker for microservices
- Need pub/sub messaging for LearnFlow platform

## Instructions

### Deploy Kafka
1. Run deployment: `python scripts/deploy.py --namespace kafka --replicas 1`
2. Wait for completion (shows progress)
3. Verify status: `python scripts/verify.py --namespace kafka`

### Create Topics
1. List topics: `python scripts/topic_manager.py list --namespace kafka`
2. Create topic: `python scripts/topic_manager.py create <topic-name> --partitions 3 --replicas 1`
3. Delete topic: `python scripts/topic_manager.py delete <topic-name>`

### Test Connectivity
1. Run test producer: `python scripts/test_connection.py produce --namespace kafka`
2. Run test consumer: `python scripts/test_connection.py consume --namespace kafka`

## Validation
- [ ] All Kafka pods in Running state
- [ ] Zookeeper pods healthy
- [ ] Can create and list topics
- [ ] Producer/consumer test successful

## Configuration Options
- `--replicas`: Number of Kafka brokers (default: 1 for dev, 3 for prod)
- `--persistence`: Enable persistent storage (default: false for dev)
- `--resources`: CPU/memory limits

See [REFERENCE.md](./REFERENCE.md) for advanced configuration and troubleshooting.
