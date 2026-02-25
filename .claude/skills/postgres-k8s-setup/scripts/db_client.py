#!/usr/bin/env python3
"""
Database Client - Connect, backup, restore, and run queries

Usage:
    python db_client.py connect --namespace database
    python db_client.py backup --namespace database --output backup.sql
    python db_client.py restore --namespace database --input backup.sql
    python db_client.py query --namespace database --sql "SELECT * FROM users;"
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def run_command(cmd: list, capture: bool = True) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=300
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


def connect_info(namespace: str) -> bool:
    """Print connection information."""
    print(f"PostgreSQL Connection Info - Namespace: {namespace}")
    print("=" * 60)
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    # Get service info
    cmd = ["kubectl", "get", "svc", "postgresql", "-n", namespace, "-o", "wide"]
    success, stdout, _ = run_command(cmd)
    
    print("\nService:")
    if success:
        print(stdout)
    
    print("\nConnection Methods:")
    print(f"\n1. Port Forward (local connection):")
    print(f"   kubectl port-forward svc/postgresql -n {namespace} 5432:5432")
    print(f"   Connection string: postgresql://postgres:PASSWORD@localhost:5432/learnflow")
    
    print(f"\n2. Direct (from cluster):")
    print(f"   Host: postgresql.{namespace}.svc.cluster.local")
    print(f"   Port: 5432")
    print(f"   Database: learnflow")
    
    print(f"\n3. Exec into pod:")
    print(f"   kubectl exec -it -n {namespace} {pod} -- psql -U postgres -d learnflow")
    
    return True


def backup_database(namespace: str, output: str) -> bool:
    """Backup database to SQL file."""
    print(f"Backing up database from namespace '{namespace}'...")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    # Generate filename if not provided
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"backup_{timestamp}.sql"
    
    output_path = Path(output)
    
    print(f"  Output file: {output_path.absolute()}")
    
    # Run pg_dump
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "pg_dump", "-U", "postgres", "-d", "learnflow"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        with open(output_path, 'w') as f:
            f.write(stdout)
        
        file_size = output_path.stat().st_size
        print(f"✓ Backup completed: {file_size / 1024:.2f} KB")
        return True
    else:
        print(f"✗ Backup failed: {stderr}")
        return False


def restore_database(namespace: str, input_file: str) -> bool:
    """Restore database from SQL file."""
    print(f"Restoring database to namespace '{namespace}'...")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"✗ File not found: {input_path.absolute()}")
        return False
    
    print(f"  Input file: {input_path.absolute()}")
    
    # Confirm restore
    confirm = input("  ⚠ This will overwrite existing data. Continue? [y/N]: ")
    if confirm.lower() != 'y':
        print("  Cancelled")
        return True
    
    with open(input_path, 'r') as f:
        sql = f.read()
    
    # Run psql restore
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
        print("✓ Restore completed successfully")
        return True
    else:
        print(f"✗ Restore failed: {stderr[:200]}")
        return False


def run_query(namespace: str, sql: str) -> bool:
    """Run SQL query."""
    print(f"Running query in namespace '{namespace}'...")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow",
        "-c", sql
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"\n{stdout}")
        return True
    else:
        print(f"✗ Query failed: {stderr}")
        return False


def run_interactive(namespace: str) -> bool:
    """Start interactive psql session."""
    print(f"Starting interactive psql session...")
    print("Type \\q to quit\n")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-it", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow"
    ]
    
    # Run interactively
    subprocess.run(cmd)
    return True


def show_tables(namespace: str) -> bool:
    """List all tables."""
    print(f"Tables in namespace '{namespace}'...")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("✗ No PostgreSQL pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow",
        "-c", "\\dt"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"\n{stdout}")
        return True
    else:
        print(f"✗ Failed: {stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Database Client"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # connect (show info)
    connect_parser = subparsers.add_parser("connect", help="Show connection info")
    connect_parser.add_argument("-n", "--namespace", default="database",
                               help="Namespace (default: database)")
    
    # backup
    backup_parser = subparsers.add_parser("backup", help="Backup database")
    backup_parser.add_argument("-n", "--namespace", default="database",
                              help="Namespace (default: database)")
    backup_parser.add_argument("-o", "--output", help="Output file path")
    
    # restore
    restore_parser = subparsers.add_parser("restore", help="Restore database")
    restore_parser.add_argument("-n", "--namespace", default="database",
                               help="Namespace (default: database)")
    restore_parser.add_argument("-i", "--input", required=True,
                               help="Input SQL file path")
    
    # query
    query_parser = subparsers.add_parser("query", help="Run SQL query")
    query_parser.add_argument("-n", "--namespace", default="database",
                             help="Namespace (default: database)")
    query_parser.add_argument("-s", "--sql", required=True,
                             help="SQL query to run")
    
    # interactive
    interactive_parser = subparsers.add_parser("interactive", help="Interactive psql")
    interactive_parser.add_argument("-n", "--namespace", default="database",
                                   help="Namespace (default: database)")
    
    # tables
    tables_parser = subparsers.add_parser("tables", help="List tables")
    tables_parser.add_argument("-n", "--namespace", default="database",
                              help="Namespace (default: database)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "connect":
        success = connect_info(args.namespace)
    elif args.command == "backup":
        success = backup_database(args.namespace, args.output)
    elif args.command == "restore":
        success = restore_database(args.namespace, args.input)
    elif args.command == "query":
        success = run_query(args.namespace, args.sql)
    elif args.command == "interactive":
        success = run_interactive(args.namespace)
    elif args.command == "tables":
        success = show_tables(args.namespace)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
