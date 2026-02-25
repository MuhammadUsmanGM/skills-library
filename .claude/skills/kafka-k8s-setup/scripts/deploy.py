#!/usr/bin/env python3
"""
Deploy Apache Kafka on Kubernetes using Helm

Usage:
    python deploy.py --namespace kafka --replicas 1
    python deploy.py --namespace kafka --replicas 3 --persistence
"""

import argparse
import subprocess
import sys
import time
import json
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


def check_prerequisites() -> bool:
    """Check if kubectl and helm are available."""
    print("\nChecking prerequisites...")
    
    # Check kubectl
    success, _, stderr = run_command(["kubectl", "version", "--client"])
    if not success:
        print(f"✗ kubectl not found: {stderr}")
        return False
    print("✓ kubectl available")
    
    # Check helm
    success, _, stderr = run_command(["helm", "version"])
    if not success:
        print(f"✗ helm not found: {stderr}")
        return False
    print("✓ helm available")
    
    # Check cluster connection
    success, stdout, stderr = run_command(["kubectl", "cluster-info"])
    if not success:
        print(f"✗ Cannot connect to cluster: {stderr}")
        return False
    print("✓ Connected to Kubernetes cluster")
    
    return True


def create_namespace(namespace: str) -> bool:
    """Create namespace if not exists."""
    print(f"\nEnsuring namespace '{namespace}' exists...")
    
    # Check if exists
    success, _, _ = run_command(["kubectl", "get", "namespace", namespace])
    if success:
        print(f"  Namespace '{namespace}' already exists")
        return True
    
    # Create namespace
    ns_yaml = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
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
    
    # Check if repo exists
    success, stdout, _ = run_command(["helm", "repo", "list"])
    if "bitnami" in stdout:
        print("  Bitnami repository already exists")
        return True
    
    # Add repository
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
    
    success, stdout, stderr = run_command(["helm", "repo", "update"])
    
    if success:
        print("✓ Repositories updated")
        return True
    else:
        print(f"✗ Failed to update: {stderr}")
        return False


def search_kafka_chart() -> Optional[str]:
    """Search for Kafka chart and return latest version."""
    print("\nSearching for Kafka chart...")
    
    success, stdout, stderr = run_command([
        "helm", "search", "repo", "bitnami/kafka",
        "--versions", "-o", "json"
    ])
    
    if not success:
        print(f"✗ Failed to search: {stderr}")
        return None
    
    try:
        charts = json.loads(stdout)
        if charts:
            # Get latest version (first result)
            latest = charts[0]
            version = latest.get("version", "")
            print(f"✓ Found Kafka chart version: {version}")
            return version
    except json.JSONDecodeError:
        pass
    
    # Fallback to known stable version
    print("  Using default version: 22.0.0")
    return "22.0.0"


def install_kafka(
    namespace: str,
    replicas: int = 1,
    persistence: bool = False,
    chart_version: Optional[str] = None
) -> bool:
    """Install Kafka using Helm."""
    print(f"\nInstalling Kafka (replicas={replicas}, persistence={persistence})...")
    
    cmd = [
        "helm", "install", "kafka", "bitnami/kafka",
        "--namespace", namespace,
        "--wait",
        "--timeout", "10m0s"
    ]
    
    # Basic configuration
    cmd.extend([
        "--set", f"replicaCount={replicas}",
        "--set", f"controller.replicas={replicas}",
        "--set", "controller.controllerOnly=false",
        "--set", "zookeeper.replicaCount=1",
    ])
    
    # Persistence settings
    if persistence:
        cmd.extend([
            "--set", "persistence.enabled=true",
            "--set", "persistence.size=10Gi",
            "--set", "zookeeper.persistence.enabled=true",
            "--set", "zookeeper.persistence.size=5Gi",
        ])
    else:
        # Development mode - no persistence
        cmd.extend([
            "--set", "persistence.enabled=false",
            "--set", "zookeeper.persistence.enabled=false",
        ])
    
    # Resource limits for development
    if replicas == 1:
        cmd.extend([
            "--set", "resources.limits.cpu=500m",
            "--set", "resources.limits.memory=1Gi",
            "--set", "resources.requests.cpu=250m",
            "--set", "resources.requests.memory=512Mi",
            "--set", "zookeeper.resources.limits.cpu=500m",
            "--set", "zookeeper.resources.limits.memory=512Mi",
        ])
    
    # Add chart version if specified
    if chart_version:
        cmd.extend(["--version", chart_version])
    
    success, stdout, stderr = run_command(cmd, capture=False)
    
    if success:
        print("\n✓ Kafka installation initiated")
        return True
    else:
        print(f"\n✗ Installation failed: {stderr}")
        # Check if already installed
        if "already exists" in stderr.lower():
            print("  Kafka may already be installed. Use 'helm uninstall kafka' first.")
        return False


def get_installation_status(namespace: str) -> str:
    """Get current installation status."""
    success, stdout, stderr = run_command([
        "helm", "status", "kafka",
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
    """Wait for Kafka installation to complete."""
    print(f"\nWaiting for Kafka to be ready (timeout: {timeout}s)...")
    print("-" * 50)
    
    start_time = time.time()
    last_status = ""
    
    while time.time() - start_time < timeout:
        # Check Helm status
        status = get_installation_status(namespace)
        
        if status != last_status:
            print(f"  Helm status: {status}")
            last_status = status
        
        if status == "deployed":
            # Verify pods are running
            success, stdout, _ = run_command([
                "kubectl", "get", "pods", "-n", namespace,
                "-l", "app.kubernetes.io/name=kafka",
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
                        print(f"✓ Kafka is ready! ({len(pods)} pods running)")
                        return True
                    
                except json.JSONDecodeError:
                    pass
        
        elif status in ["failed", "uninstalling"]:
            print(f"\n✗ Installation status: {status}")
            return False
        
        elapsed = int(time.time() - start_time)
        print(f"  Waiting... ({elapsed}s/{timeout}s)")
        time.sleep(15)
    
    print(f"\n✗ Timeout waiting for Kafka to be ready")
    print("\nDebug commands:")
    print(f"  kubectl get pods -n {namespace}")
    print(f"  kubectl describe pods -n {namespace}")
    print(f"  kubectl logs -n {namespace} -l app.kubernetes.io/name=kafka")
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Apache Kafka on Kubernetes"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="kafka",
        help="Target namespace (default: kafka)"
    )
    parser.add_argument(
        "-r", "--replicas",
        type=int,
        default=1,
        help="Number of Kafka brokers (default: 1)"
    )
    parser.add_argument(
        "-p", "--persistence",
        action="store_true",
        help="Enable persistent storage"
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
    print("Kafka Kubernetes Deployment")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites check failed")
        sys.exit(1)
    
    # Create namespace
    if not create_namespace(args.namespace):
        sys.exit(1)
    
    # Add Bitnami repo
    if not add_bitnami_repo():
        sys.exit(1)
    
    # Update repos
    if not update_repos():
        sys.exit(1)
    
    # Find chart version
    chart_version = search_kafka_chart()
    
    # Install Kafka
    if not install_kafka(
        namespace=args.namespace,
        replicas=args.replicas,
        persistence=args.persistence,
        chart_version=chart_version
    ):
        sys.exit(1)
    
    if args.no_wait:
        print("\n⚠ Not waiting for installation to complete")
        print("Check status with: helm status kafka -n {}".format(args.namespace))
        sys.exit(0)
    
    # Wait for installation
    success = wait_for_installation(args.namespace, args.timeout)
    
    if success:
        print("\n✓ Kafka deployment complete!")
        print(f"\nConnect to Kafka:")
        print(f"  kubectl port-forward svc/kafka -n {args.namespace} 9092:9092")
        print(f"\nBootstrap server: localhost:9092")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
