---
name: postgres-k8s-setup
description: Deploy PostgreSQL on Kubernetes with migrations
---

# PostgreSQL Kubernetes Setup

## When to Use
- Deploying database for LearnFlow platform
- Setting up PostgreSQL for microservices
- Need persistent data storage with migrations

## Instructions

### Deploy PostgreSQL
1. Run deployment: `python scripts/deploy.py --namespace database --password SecurePass123!`
2. Wait for completion (shows progress)
3. Verify status: `python scripts/verify.py --namespace database`

### Run Migrations
1. Create migration: `python scripts/migration_manager.py create <migration_name>`
2. Apply migrations: `python scripts/migration_manager.py apply --namespace database`
3. Check status: `python scripts/migration_manager.py status --namespace database`

### Database Operations
1. Connect: `python scripts/db_client.py connect --namespace database`
2. Backup: `python scripts/db_client.py backup --namespace database --output backup.sql`
3. Restore: `python scripts/db_client.py restore --namespace database --input backup.sql`

## Validation
- [ ] PostgreSQL pod in Running state
- [ ] Can connect to database
- [ ] Migrations applied successfully
- [ ] Data persisted after restart

## Configuration Options
- `--password`: Database password (required)
- `--database`: Database name (default: learnflow)
- `--persistence`: Enable persistent storage (default: true)
- `--size`: Storage size (default: 5Gi)

See [REFERENCE.md](./REFERENCE.md) for advanced configuration and troubleshooting.
