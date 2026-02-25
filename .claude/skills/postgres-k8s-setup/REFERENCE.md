# PostgreSQL Kubernetes Reference

## Quick Start

```bash
# Deploy PostgreSQL (development)
python scripts/deploy.py --namespace database --password SecurePass123!

# Verify installation
python scripts/verify.py --namespace database

# Apply migrations
python scripts/migration_manager.py apply --namespace database

# Backup database
python scripts/db_client.py backup --namespace database --output backup.sql
```

## Production Deployment

```bash
# Deploy with persistence and larger storage
python scripts/deploy.py \
  --namespace database \
  --password SecurePass123! \
  --persistence \
  --size 20Gi
```

## Helm Chart Configuration

### Development

```yaml
auth:
  postgresPassword: securepassword
  database: learnflow
  username: learnflow
  password: securepassword
primary:
  persistence:
    enabled: false
  resources:
    limits:
      cpu: 1
      memory: 1Gi
    requests:
      cpu: 250m
      memory: 512Mi
```

### Production

```yaml
auth:
  postgresPassword: <secure-password>
  database: learnflow
  username: learnflow
  password: <secure-password>
primary:
  persistence:
    enabled: true
    size: 20Gi
    storageClass: standard
  resources:
    limits:
      cpu: 2
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 1Gi
  extendedConfiguration: |
    max_connections=200
    shared_buffers=512MB
    effective_cache_size=1536MB
```

## LearnFlow Database Schema

### Core Tables

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- student, teacher
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Student progress
CREATE TABLE student_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    module_id VARCHAR(50) NOT NULL,
    mastery_score DECIMAL(5,2) DEFAULT 0,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Code submissions
CREATE TABLE code_submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    exercise_id VARCHAR(50) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(50) NOT NULL, -- pending, success, error
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Struggle events
CREATE TABLE struggle_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    context JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Common Operations

### Create Migration

```bash
python scripts/migration_manager.py create "add_users_table"
```

This creates a file like: `migrations/20260225120000_add_users_table.sql`

### Apply Migrations

```bash
python scripts/migration_manager.py apply --namespace database
```

### Check Status

```bash
python scripts/migration_manager.py status --namespace database
```

### Rollback Migration

```bash
python scripts/migration_manager.py rollback 20260225120000 --namespace database
```

## Manual PostgreSQL Commands

```bash
# Get PostgreSQL pod
POD=$(kubectl get pods -n database -l app.kubernetes.io/name=postgresql \
  -o jsonpath='{.items[0].metadata.name}')

# Connect to database
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow

# List databases
kubectl exec -it -n database $POD -- psql -U postgres -c "\\l"

# List tables
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow -c "\\dt"

# Describe table
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow -c "\\d users"

# Run query
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  -c "SELECT COUNT(*) FROM users;"

# Export data
kubectl exec -it -n database $POD -- pg_dump -U postgres -d learnflow \
  > backup.sql

# Import data
kubectl exec -i -n database $POD -- psql -U postgres -d learnflow \
  < backup.sql
```

## Backup and Restore

### Automated Backup Script

```bash
#!/bin/bash
# Daily backup script

NAMESPACE="database"
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)

kubectl exec -n $NAMESPACE postgresql-0 -- pg_dump -U postgres -d learnflow \
  > ${BACKUP_DIR}/backup_${DATE}.sql

# Keep only last 7 days
find ${BACKUP_DIR} -name "backup_*.sql" -mtime +7 -delete
```

### Restore from Backup

```bash
python scripts/db_client.py restore \
  --namespace database \
  --input backup_20260225_120000.sql
```

## Monitoring

### Check Pod Status

```bash
kubectl get pods -n database -l app.kubernetes.io/name=postgresql
```

### View Logs

```bash
kubectl logs -n database -l app.kubernetes.io/name=postgresql -f
```

### Check Connections

```bash
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  -c "SELECT count(*) FROM pg_stat_activity;"
```

### Check Database Size

```bash
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  -c "SELECT pg_size_pretty(pg_database_size('learnflow'));"
```

## Troubleshooting

### Issue: Pod won't start

```bash
# Check events
kubectl describe pods -n database -l app.kubernetes.io/name=postgresql

# Check PVC
kubectl get pvc -n database
kubectl describe pvc -n database

# Check for insufficient resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### Issue: Cannot connect to database

```bash
# Check service
kubectl get svc -n database

# Check if pod is ready
kubectl get pods -n database -l app.kubernetes.io/name=postgresql

# Test connection from within cluster
kubectl run test --rm -it --image=postgres:15 -- psql \
  -h postgresql.database.svc.cluster.local -U postgres -d learnflow
```

### Issue: Migration fails

```bash
# Check migrations table
python scripts/db_client.py query --namespace database \
  --sql "SELECT * FROM schema_migrations ORDER BY id;"

# Manually apply migration
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  < migrations/20260225120000_migration.sql
```

### Issue: Database is slow

```bash
# Check active queries
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check for locks
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Analyze slow queries (requires pg_stat_statements)
kubectl exec -it -n database $POD -- psql -U postgres -d learnflow \
  -c "SELECT query, calls, total_time FROM pg_stat_statements \
      ORDER BY total_time DESC LIMIT 10;"
```

## Performance Tuning

### Recommended Settings (Production)

```yaml
# In Helm values
primary:
  extendedConfiguration: |
    # Memory
    shared_buffers = 512MB
    effective_cache_size = 1536MB
    work_mem = 16MB
    maintenance_work_mem = 128MB
    
    # Connections
    max_connections = 200
    
    # WAL
    wal_buffers = 16MB
    checkpoint_completion_target = 0.9
    
    # Query planning
    random_page_cost = 1.1
    effective_io_concurrency = 200
```

### Indexing Best Practices

```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_student_progress_user ON student_progress(user_id);
CREATE INDEX idx_code_submissions_user ON code_submissions(user_id);
CREATE INDEX idx_struggle_events_user ON struggle_events(user_id);

-- Composite indexes for common queries
CREATE INDEX idx_progress_user_module ON student_progress(user_id, module_id);
```

## Security

### Change Default Password

```bash
# Update password secret
kubectl create secret generic postgresql \
  --from-literal=postgres-password=newsecurepassword \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pod to pick up new password
kubectl rollout restart statefulset postgresql -n database
```

### Enable Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgresql-network-policy
  namespace: database
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: postgresql
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: apps
    ports:
    - protocol: TCP
      port: 5432
```

## Related Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Bitnami PostgreSQL Helm Chart](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
