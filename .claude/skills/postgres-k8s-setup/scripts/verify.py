#!/usr/bin/env python3
"""
Verify PostgreSQL Installation

Usage: python verify.py --namespace database
"""

import argparse
import subprocess
import json
import sys
from typing import List, Dict, Optional


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


def get_pods(namespace: str, labels: Optional[str] = None) -> List[Dict]:
    """Get pods in namespace."""
    cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
    if labels:
        cmd.extend(["-l", labels])
    
    success, stdout, _ = run_command(cmd)
    if not success:
        return []
    
    try:
        data = json.loads(stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def check_pod_status(pod: Dict) -> Dict:
    """Check pod status."""
    name = pod["metadata"]["name"]
    status = pod.get("status", {})
    phase = status.get("phase", "Unknown")
    
    container_statuses = status.get("containerStatuses", [])
    ready_count = sum(1 for cs in container_statuses if cs.get("ready", False))
    total_containers = len(container_statuses)
    
    return {
        "name": name,
        "phase": phase,
        "ready": f"{ready_count}/{total_containers}",
        "restarts": sum(cs.get("restartCount", 0) for cs in container_statuses)
    }


def get_postgresql_pod(namespace: str) -> Optional[str]:
    """Get PostgreSQL pod name."""
    pods = get_pods(namespace, "app.kubernetes.io/name=postgresql")
    if pods:
        return pods[0]["metadata"]["name"]
    return None


def test_database_connection(namespace: str) -> bool:
    """Test database connection."""
    print("\nTesting database connection...")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        print("  ✗ No PostgreSQL pod found")
        return False
    
    # Try to connect and run a simple query
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-d", "learnflow",
        "-c", "SELECT 1;"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("  ✓ Can connect to PostgreSQL")
        return True
    else:
        print(f"  ✗ Cannot connect: {stderr[:100]}")
        return False


def list_databases(namespace: str) -> bool:
    """List databases."""
    print("\nDatabases:")
    
    pod = get_postgresql_pod(namespace)
    if not pod:
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, pod, "--",
        "psql", "-U", "postgres", "-c", "\\l"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(stdout)
        return True
    else:
        print(f"  Error: {stderr[:100]}")
        return False


def verify_postgresql_installation(namespace: str) -> bool:
    """Verify PostgreSQL installation."""
    print("=" * 60)
    print(f"PostgreSQL Installation Verification - Namespace: {namespace}")
    print("=" * 60)
    
    all_healthy = True
    
    # Check pods
    print("\n📦 PostgreSQL Pods:")
    pods = get_pods(namespace, "app.kubernetes.io/name=postgresql")
    
    if not pods:
        print("  ✗ No PostgreSQL pods found")
        all_healthy = False
    else:
        for pod in pods:
            status = check_pod_status(pod)
            icon = "✓" if status["phase"] == "Running" else "⚠"
            print(f"  {icon} {status['name']}: {status['phase']} "
                  f"(ready: {status['ready']}, restarts: {status['restarts']})")
            if status["phase"] != "Running":
                all_healthy = False
    
    # Check services
    print("\n🌐 Services:")
    cmd = ["kubectl", "get", "services", "-n", namespace, "-o", "wide"]
    success, stdout, _ = run_command(cmd)
    
    if success:
        print(stdout)
    else:
        print("  ✗ No services found")
        all_healthy = False
    
    # Test connection
    if pods:
        if not test_database_connection(namespace):
            all_healthy = False
        
        # List databases
        list_databases(namespace)
    
    # Summary
    print("\n" + "=" * 60)
    if all_healthy:
        print("✓ PostgreSQL installation is healthy!")
    else:
        print("⚠ PostgreSQL installation has issues")
        print("\nDebug commands:")
        print(f"  kubectl describe pods -n {namespace}")
        print(f"  kubectl logs -n {namespace} -l app.kubernetes.io/name=postgresql")
    
    return all_healthy


def main():
    parser = argparse.ArgumentParser(
        description="Verify PostgreSQL installation"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="database",
        help="Namespace to check (default: database)"
    )
    
    args = parser.parse_args()
    
    success = verify_postgresql_installation(args.namespace)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
