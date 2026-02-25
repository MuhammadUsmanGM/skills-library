#!/usr/bin/env python3
"""
Database Migration Manager - Create, apply, and track migrations

Usage:
    python migration_manager.py create <migration_name>
    python migration_manager.py apply --namespace database
    python migration_manager.py status --namespace database
    python migration_manager.py list --namespace database
"""

import argparse
import subprocess
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict


MIGRATIONS_DIR = Path("migrations")


def run_command(cmd: list) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def get_postgresql_pod(namespace: str) -> Optional[str]:
    """Get PostgreSQL pod name."""
    cmd = [
        "kubectl", "get", "pods", "-n", namespace,
        "-l", "app.kubernetes.io/name=postgresql",
        "-o", "jsonpath={.items[0].metadata.name}"
    ]
    
    success, stdout, _ = run_command(cmd)
    return stdout if success and stdout else None


def ensure_migrations_table(namespace: str) -> bool:
    """Create migrations tracking table if not exists."""
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        version VARCHAR(255) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        checksum VARCHAR(64)
    );
    """
    
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow",
        "-c", sql
    ]
    
    success, _, stderr = run_command(cmd)
    if success:
        print("✓ Migrations table ready")
        return True
    else:
        print(f"✗ Failed to create migrations table: {stderr}")
        return False


def get_applied_migrations(namespace: str) -> List[Dict]:
    """Get list of applied migrations."""
    pod = get_postgresql_pod(namespace)
    if not pod:
        return []
    
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow",
        "-c", "SELECT version, name, applied_at FROM schema_migrations ORDER BY id;",
        "-t", "-A", "-F", "|"
    ]
    
    success, stdout, _ = run_command(cmd)
    
    if not success:
        return []
    
    migrations = []
    for line in stdout.strip().split('\n'):
        if line:
            parts = line.split('|')
            if len(parts) >= 3:
                migrations.append({
                    "version": parts[0],
                    "name": parts[1],
                    "applied_at": parts[2]
                })
    
    return migrations


def create_migration(name: str) -> bool:
    """Create a new migration file."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    version = timestamp
    filename = f"{version}_{name.lower().replace(' ', '_')}.sql"
    
    # Ensure migrations directory exists
    MIGRATIONS_DIR.mkdir(exist_ok=True)
    
    migration_path = MIGRATIONS_DIR / filename
    
    # Create migration content
    content = f"""-- Migration: {name}
-- Version: {version}
-- Created: {datetime.now().isoformat()}

-- Write your migration SQL here
-- Example:
-- CREATE TABLE IF NOT EXISTS example_table (
--     id SERIAL PRIMARY KEY,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Down migration (rollback)
-- DROP TABLE IF EXISTS example_table;
"""
    
    with open(migration_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Created migration: {filename}")
    print(f"  Path: {migration_path.absolute()}")
    return True


def apply_migrations(namespace: str) -> bool:
    """Apply pending migrations."""
    print(f"Applying migrations to namespace '{namespace}'...")
    
    # Ensure migrations table exists
    if not ensure_migrations_table(namespace):
        return False
    
    # Get applied migrations
    applied = {m["version"] for m in get_applied_migrations(namespace)}
    print(f"  Applied migrations: {len(applied)}")
    
    # Get migration files
    if not MIGRATIONS_DIR.exists():
        print("  No migrations directory found")
        return True
    
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    
    if not migration_files:
        print("  No migration files found")
        return True
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    # Apply each pending migration
    applied_count = 0
    for migration_file in migration_files:
        # Extract version from filename
        version = migration_file.stem.split('_')[0]
        
        if version in applied:
            print(f"  ⊘ Skipping {migration_file.name} (already applied)")
            continue
        
        print(f"  Applying {migration_file.name}...")
        
        # Read migration content
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        # Extract just the up migration (before "Down migration" comment)
        if "-- Down migration" in sql:
            sql = sql.split("-- Down migration")[0]
        
        # Execute migration
        cmd = [
            "kubectl", "exec", "-n", namespace, pod, "--",
            "psql", "-U", "postgres", "-d", "learnflow",
            "-f", "-"
        ]
        
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input=sql)
        
        if proc.returncode == 0:
            # Record migration
            record_cmd = [
                "kubectl", "exec", "-n", namespace, pod, "--",
                "psql", "-U", "postgres", "-d", "learnflow",
                "-c",
                f"INSERT INTO schema_migrations (version, name) VALUES ('{version}', '{migration_file.name}');"
            ]
            
            run_command(record_cmd)
            print(f"    ✓ Applied")
            applied_count += 1
        else:
            print(f"    ✗ Failed: {stderr[:100]}")
            return False
    
    print(f"\n✓ Applied {applied_count} migration(s)")
    return True


def show_status(namespace: str) -> bool:
    """Show migration status."""
    print(f"Migration Status - Namespace: {namespace}")
    print("=" * 60)
    
    applied = get_applied_migrations(namespace)
    
    if not applied:
        print("\nNo migrations applied yet")
    else:
        print(f"\nApplied Migrations ({len(applied)}):")
        for m in applied:
            print(f"  ✓ {m['version']} - {m['name']} (applied: {m['applied_at']})")
    
    # Check for pending migrations
    if MIGRATIONS_DIR.exists():
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        applied_versions = {m["version"] for m in applied}
        
        pending = []
        for f in migration_files:
            version = f.stem.split('_')[0]
            if version not in applied_versions:
                pending.append(f.name)
        
        if pending:
            print(f"\nPending Migrations ({len(pending)}):")
            for p in pending:
                print(f"  ⏳ {p}")
        else:
            print("\n✓ All migrations are up to date")
    
    return True


def list_migrations(namespace: str) -> bool:
    """List all migrations (applied and pending)."""
    print(f"All Migrations - Namespace: {namespace}")
    print("=" * 60)
    
    applied = {m["version"]: m for m in get_applied_migrations(namespace)}
    
    if MIGRATIONS_DIR.exists():
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        
        for f in migration_files:
            version = f.stem.split('_')[0]
            name = '_'.join(f.stem.split('_')[1:])
            
            if version in applied:
                m = applied[version]
                print(f"  ✓ {f.name} (applied: {m['applied_at']})")
            else:
                print(f"  ⏳ {f.name} (pending)")
    else:
        print("  No migrations directory found")
    
    return True


def rollback_migration(namespace: str, version: str) -> bool:
    """Rollback a specific migration."""
    print(f"Rolling back migration {version}...")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    # Find migration file
    migration_files = list(MIGRATIONS_DIR.glob(f"{version}_*.sql"))
    
    if not migration_files:
        print(f"✗ Migration file not found for version {version}")
        return False
    
    migration_file = migration_files[0]
    
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Extract down migration
    if "-- Down migration" not in content:
        print("✗ No down migration found in file")
        return False
    
    down_sql = content.split("-- Down migration")[1].strip()
    
    # Execute rollback
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow",
        "-c", down_sql
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        # Remove from tracking table
        run_command([
            "kubectl", "exec", "-n", namespace, pod, "--",
            "psql", "-U", "postgres", "-d", "learnflow",
            "-c", f"DELETE FROM schema_migrations WHERE version = '{version}';"
        ])
        
        print(f"✓ Rolled back migration {version}")
        return True
    else:
        print(f"✗ Rollback failed: {stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Database Migration Manager"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # create
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("name", help="Migration name")
    
    # apply
    apply_parser = subparsers.add_parser("apply", help="Apply pending migrations")
    apply_parser.add_argument("-n", "--namespace", default="database",
                             help="Namespace (default: database)")
    
    # status
    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.add_argument("-n", "--namespace", default="database",
                              help="Namespace (default: database)")
    
    # list
    list_parser = subparsers.add_parser("list", help="List all migrations")
    list_parser.add_argument("-n", "--namespace", default="database",
                            help="Namespace (default: database)")
    
    # rollback
    rollback_parser = subparsers.add_parser("rollback", help="Rollback a migration")
    rollback_parser.add_argument("version", help="Migration version to rollback")
    rollback_parser.add_argument("-n", "--namespace", default="database",
                                help="Namespace (default: database)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "create":
        success = create_migration(args.name)
    elif args.command == "apply":
        success = apply_migrations(args.namespace)
    elif args.command == "status":
        success = show_status(args.namespace)
    elif args.command == "list":
        success = list_migrations(args.namespace)
    elif args.command == "rollback":
        success = rollback_migration(args.namespace, args.version)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
