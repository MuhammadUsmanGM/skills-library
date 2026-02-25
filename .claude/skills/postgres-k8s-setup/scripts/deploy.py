#!/usr/bin/env python3
"""
Deploy PostgreSQL on Kubernetes using Helm

Usage:
    python deploy.py --namespace database --password SecurePass123!
    python deploy.py --namespace database --password SecurePass123! --persistence
"""

import argparse
import subprocess
import sys
import time
import json
import secrets
import string
from typing import Optional


def run_command(cmd: list, capture: bool = True, input_data: Optional[str] = None) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    print(f"  $ {' '.join(cmd)}")
    try:
        if input_data:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=input_data)
            return proc.returncode == 0, stdout, stderr
        else:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=300
            )
            return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError as e:
        return False, "", f"Command not found: {e}"


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def check_prerequisites() -> bool:
    """Check if kubectl and helm are available."""
    print("\nChecking prerequisites...")
    
    success, _, stderr = run_command(["kubectl", "version", "--client"])
    if not success:
        print(f"✗ kubectl not found: {stderr}")
        return False
    print("✓ kubectl available")
    
    success, _, stderr = run_command(["helm", "version"])
    if not success:
        print(f"✗ helm not found: {stderr}")
        return False
    print("✓ helm available")
    
    success, _, stderr = run_command(["kubectl", "cluster-info"])
    if not success:
        print(f"✗ Cannot connect to cluster: {stderr}")
        return False
    print("✓ Connected to Kubernetes cluster")
    
    return True


def create_namespace(namespace: str) -> bool:
    """Create namespace if not exists."""
    print(f"\nEnsuring namespace '{namespace}' exists...")
    
    success, _, _ = run_command(["kubectl", "get", "namespace", namespace])
    if success:
        print(f"  Namespace '{namespace}' already exists")
        return True
    
    ns_yaml = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
"""
    
    success, stdout, stderr = run_command(
        ["kubectl", "apply", "-f", "-"],
        input_data=ns_yaml
    )
    
    if success:
        print(f"✓ Namespace '{namespace}' created")
        return True
    else:
        print(f"✗ Failed to create namespace: {stderr}")
        return False


def add_bitnami_repo() -> bool:
    """Add Bitnami Helm repository."""
    print("\nAdding Bitnami Helm repository...")
    
    success, stdout, _ = run_command(["helm", "repo", "list"])
    if "bitnami" in stdout:
        print("  Bitnami repository already exists")
        return True
    
    success, stdout, stderr = run_command([
        "helm", "repo", "add", "bitnami",
        "https://charts.bitnami.com/bitnami"
    ])
    
    if success:
        print("✓ Bitnami repository added")
        return True
    elif "already exists" in stderr.lower():
        print("  Repository already exists")
        return True
    else:
        print(f"✗ Failed to add repository: {stderr}")
        return False


def update_repos() -> bool:
    """Update Helm repositories."""
    print("\nUpdating Helm repositories...")
    
    success, _, stderr = run_command(["helm", "repo", "update"])
    if success:
        print("✓ Repositories updated")
        return True
    else:
        print(f"✗ Failed to update: {stderr}")
        return False


def check_existing_secret(namespace: str, secret_name: str) -> Optional[str]:
    """Check if password secret already exists."""
    success, stdout, _ = run_command([
        "kubectl", "get", "secret", secret_name,
        "-n", namespace,
        "-o", "jsonpath={.data.postgres-password}"
    ])
    
    if success and stdout:
        import base64
        try:
            return base64.b64decode(stdout).decode()
        except:
            return None
    return None


def install_postgresql(
    namespace: str,
    password: str,
    database: str = "learnflow",
    persistence: bool = True,
    size: str = "5Gi"
) -> bool:
    """Install PostgreSQL using Helm."""
    print(f"\nInstalling PostgreSQL (database={database}, persistence={persistence})...")
    
    cmd = [
        "helm", "install", "postgresql", "bitnami/postgresql",
        "--namespace", namespace,
        "--wait",
        "--timeout", "10m0s"
    ]
    
    # Authentication
    cmd.extend([
        "--set", f"auth.postgresPassword={password}",
        "--set", f"auth.database={database}",
        "--set", "auth.username=learnflow",
        "--set", f"auth.password={password}",
    ])
    
    # Persistence
    if persistence:
        cmd.extend([
            "--set", "primary.persistence.enabled=true",
            "--set", f"primary.persistence.size={size}",
        ])
    else:
        cmd.extend([
            "--set", "primary.persistence.enabled=false",
        ])
    
    # Resources for development
    cmd.extend([
        "--set", "primary.resources.limits.cpu=1",
        "--set", "primary.resources.limits.memory=1Gi",
        "--set", "primary.resources.requests.cpu=250m",
        "--set", "primary.resources.requests.memory=512Mi",
    ])
    
    success, stdout, stderr = run_command(cmd, capture=False)
    
    if success:
        print("\n✓ PostgreSQL installation initiated")
        return True
    else:
        print(f"\n✗ Installation failed: {stderr}")
        if "already exists" in stderr.lower():
            print("  PostgreSQL may already be installed.")
        return False


def get_installation_status(namespace: str) -> str:
    """Get current installation status."""
    success, stdout, stderr = run_command([
        "helm", "status", "postgresql",
        "--namespace", namespace,
        "-o", "json"
    ])
    
    if not success:
        return "not_found"
    
    try:
        data = json.loads(stdout)
        info = data.get("info", {})
        return info.get("status", "unknown")
    except json.JSONDecodeError:
        return "unknown"


def wait_for_installation(namespace: str, timeout: int = 600) -> bool:
    """Wait for PostgreSQL installation to complete."""
    print(f"\nWaiting for PostgreSQL to be ready (timeout: {timeout}s)...")
    print("-" * 50)
    
    start_time = time.time()
    last_status = ""
    
    while time.time() - start_time < timeout:
        status = get_installation_status(namespace)
        
        if status != last_status:
            print(f"  Helm status: {status}")
            last_status = status
        
        if status == "deployed":
            success, stdout, _ = run_command([
                "kubectl", "get", "pods", "-n", namespace,
                "-l", "app.kubernetes.io/name=postgresql",
                "-o", "json"
            ])
            
            if success:
                try:
                    data = json.loads(stdout)
                    pods = data.get("items", [])
                    
                    if not pods:
                        print("  Waiting for pods to be created...")
                        time.sleep(10)
                        continue
                    
                    all_running = True
                    for pod in pods:
                        phase = pod.get("status", {}).get("phase", "Unknown")
                        if phase != "Running":
                            all_running = False
                            name = pod["metadata"]["name"]
                            print(f"  Pod {name}: {phase}")
                    
                    if all_running:
                        print("\n" + "=" * 50)
                        print(f"✓ PostgreSQL is ready! ({len(pods)} pods running)")
                        return True
                    
                except json.JSONDecodeError:
                    pass
        
        elif status in ["failed", "uninstalling"]:
            print(f"\n✗ Installation status: {status}")
            return False
        
        elapsed = int(time.time() - start_time)
        print(f"  Waiting... ({elapsed}s/{timeout}s)")
        time.sleep(15)
    
    print(f"\n✗ Timeout waiting for PostgreSQL to be ready")
    print("\nDebug commands:")
    print(f"  kubectl get pods -n {namespace}")
    print(f"  kubectl logs -n {namespace} -l app.kubernetes.io/name=postgresql")
    
    return False


def get_connection_info(namespace: str, password: str) -> dict:
    """Get PostgreSQL connection information."""
    return {
        "host": f"postgresql.{namespace}.svc.cluster.local",
        "port": 5432,
        "database": "learnflow",
        "username": "postgres",
        "password": password,
        "port_forward": f"kubectl port-forward svc/postgresql -n {namespace} 5432:5432"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Deploy PostgreSQL on Kubernetes"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="database",
        help="Target namespace (default: database)"
    )
    parser.add_argument(
        "-p", "--password",
        required=True,
        help="PostgreSQL password (required)"
    )
    parser.add_argument(
        "-d", "--database",
        default="learnflow",
        help="Database name (default: learnflow)"
    )
    parser.add_argument(
        "--persistence",
        action="store_true",
        default=True,
        help="Enable persistent storage (default: true)"
    )
    parser.add_argument(
        "--no-persistence",
        action="store_false",
        dest="persistence",
        help="Disable persistent storage"
    )
    parser.add_argument(
        "--size",
        default="5Gi",
        help="Storage size (default: 5Gi)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Installation timeout in seconds (default: 600)"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for installation to complete"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("PostgreSQL Kubernetes Deployment")
    print("=" * 50)
    
    if not check_prerequisites():
        print("\n✗ Prerequisites check failed")
        sys.exit(1)
    
    if not create_namespace(args.namespace):
        sys.exit(1)
    
    if not add_bitnami_repo():
        sys.exit(1)
    
    if not update_repos():
        sys.exit(1)
    
    if not install_postgresql(
        namespace=args.namespace,
        password=args.password,
        database=args.database,
        persistence=args.persistence,
        size=args.size
    ):
        sys.exit(1)
    
    if args.no_wait:
        print("\n⚠ Not waiting for installation to complete")
        sys.exit(0)
    
    success = wait_for_installation(args.namespace, args.timeout)
    
    if success:
        print("\n✓ PostgreSQL deployment complete!")
        conn = get_connection_info(args.namespace, args.password)
        print(f"\nConnection Info:")
        print(f"  Host: {conn['host']}")
        print(f"  Port: {conn['port']}")
        print(f"  Database: {conn['database']}")
        print(f"  Username: postgres")
        print(f"\nLocal connection:")
        print(f"  {conn['port_forward']}")
        print(f"  Connection string: postgresql://postgres:{args.password}@localhost:5432/{conn['database']}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
