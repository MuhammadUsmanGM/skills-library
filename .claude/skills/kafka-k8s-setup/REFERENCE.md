# Kafka Kubernetes Reference

## Quick Start

```bash
# Deploy Kafka (development - single replica, no persistence)
python scripts/deploy.py --namespace kafka --replicas 1

# Verify installation
python scripts/verify.py --namespace kafka

# Create LearnFlow topics
python scripts/topic_manager.py create-learnflow-topics --namespace kafka

# Test connection
python scripts/test_connection.py full --namespace kafka
```

## Production Deployment

```bash
# Deploy Kafka with 3 brokers and persistence
python scripts/deploy.py \
  --namespace kafka \
  --replicas 3 \
  --persistence \
  --timeout 900
```

## Helm Chart Configuration

### Development (Minimal Resources)

```yaml
replicaCount: 1
controller:
  replicas: 1
  controllerOnly: false
zookeeper:
  replicaCount: 1
persistence:
  enabled: false
zookeeper:
  persistence:
    enabled: false
resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi
```

### Production (High Availability)

```yaml
replicaCount: 3
controller:
  replicas: 3
  controllerOnly: false
zookeeper:
  replicaCount: 3
persistence:
  enabled: true
  size: 10Gi
zookeeper:
  persistence:
    enabled: true
    size: 5Gi
resources:
  limits:
    cpu: 2
    memory: 4Gi
  requests:
    cpu: 1
    memory: 2Gi
```

## Kafka Topics for LearnFlow

| Topic | Partitions | Purpose |
|-------|------------|---------|
| `learning.events` | 3 | Student learning activities |
| `code.submissions` | 3 | Code execution requests |
| `exercise.completions` | 3 | Exercise completion events |
| `struggle.alerts` | 3 | Student struggle detection |
| `progress.updates` | 3 | Progress tracking updates |

## Common Operations

### List Topics

```bash
python scripts/topic_manager.py list --namespace kafka
```

### Create Topic

```bash
python scripts/topic_manager.py create my-topic \
  --partitions 3 \
  --replicas 1 \
  --namespace kafka
```

### Describe Topic

```bash
python scripts/topic_manager.py describe my-topic --namespace kafka
```

### Delete Topic

```bash
python scripts/topic_manager.py delete my-topic --namespace kafka
```

## Manual Kafka Commands (via kubectl exec)

```bash
# Get Kafka pod
KAFKA_POD=$(kubectl get pods -n kafka -l app.kubernetes.io/name=kafka \
  -o jsonpath='{.items[0].metadata.name}')

# List topics
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

# Create topic
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic my-topic --partitions 3 --replication-factor 1

# Describe topic
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic my-topic

# Delete topic
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --topic my-topic

# Produce messages
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic my-topic

# Consume messages
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic my-topic --from-beginning --max-messages 10
```

## Port Forwarding

```bash
# Forward Kafka broker port
kubectl port-forward svc/kafka -n kafka 9092:9092

# In another terminal, test with kafka-cli or your application
# Bootstrap server: localhost:9092
```

## Monitoring

### Check Pod Status

```bash
kubectl get pods -n kafka -l app.kubernetes.io/name=kafka
kubectl get pods -n kafka -l app.kubernetes.io/name=zookeeper
```

### View Logs

```bash
# Kafka logs
kubectl logs -n kafka -l app.kubernetes.io/name=kafka -f

# Zookeeper logs
kubectl logs -n kafka -l app.kubernetes.io/name=zookeeper -f
```

### Check Resource Usage

```bash
kubectl top pods -n kafka
```

## Troubleshooting

### Issue: Pods not starting

```bash
# Check events
kubectl describe pods -n kafka -l app.kubernetes.io/name=kafka

# Check for insufficient resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Solution: Increase Minikube resources
minikube stop
minikube start --cpus=4 --memory=8192
```

### Issue: Cannot connect to broker

```bash
# Check service
kubectl get svc -n kafka

# Check broker configuration
kubectl exec -n kafka $KAFKA_POD -- \
  env | grep KAFKA

# Verify listener configuration
kubectl exec -n kafka $KAFKA_POD -- \
  cat /opt/bitnami/kafka/config/server.properties | grep listeners
```

### Issue: Topic creation fails

```bash
# Check if Kafka is ready
kubectl get pods -n kafka

# Check broker count vs replication factor
# Replication factor cannot exceed number of brokers

# List available brokers
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092
```

### Issue: High latency or slow consumers

```bash
# Check consumer lag (requires consumer group)
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group my-consumer-group

# Increase partitions for parallelism
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --alter --topic my-topic --partitions 6
```

## Backup and Restore

### Backup Topic Data

```bash
# Export messages to file
kubectl exec -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic my-topic --from-beginning --timeout-ms 60000 \
  > backup.txt
```

### Restore Topic Data

```bash
# Import messages from file
cat backup.txt | kubectl exec -i -n kafka $KAFKA_POD -- \
  /opt/bitnami/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic my-topic
```

## Security Considerations

### Enable Authentication (Production)

```yaml
# In Helm values
auth:
  enabled: true
  clientProtocol: sasl
  interbrokerProtocol: sasl
  sasl:
    mechanism: scram-sha-512
  jmx:
    enabled: true
```

### Enable TLS

```yaml
# In Helm values
tls:
  enabled: true
  type: jks
  autoGenerated: true
```

## Performance Tuning

### Broker Configuration

```yaml
# In Helm values
config:
  # Increase max message size
  message.max.bytes: 10485760
  replica.fetch.max.bytes: 10485760
  
  # Optimize for throughput
  num.network.threads: 8
  num.io.threads: 16
  socket.send.buffer.bytes: 102400
  socket.receive.buffer.bytes: 102400
  
  # Retention settings
  log.retention.hours: 168
  log.segment.bytes: 1073741824
```

## Related Resources

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Bitnami Kafka Helm Chart](https://github.com/bitnami/charts/tree/main/bitnami/kafka)
- [Kafka Best Practices](https://github.com/confluentinc/kafka-best-practices)
