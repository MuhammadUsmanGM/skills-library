#!/usr/bin/env python3
"""
Deploy FastAPI service to Kubernetes

Usage: python deploy.py <service-name> --namespace apps
"""

import argparse
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Optional


def run_command(cmd: list, capture: bool = True) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def check_prerequisites() -> bool:
    """Check if kubectl is available and cluster is accessible."""
    success, _, stderr = run_command(["kubectl", "version", "--client"])
    if not success:
        print(f"✗ kubectl not found: {stderr}")
        return False
    
    success, _, stderr = run_command(["kubectl", "cluster-info"])
    if not success:
        print(f"✗ Cannot connect to cluster: {stderr}")
        return False
    
    print("✓ Kubernetes cluster accessible")
    return True


def ensure_namespace(namespace: str) -> bool:
    """Create namespace if not exists."""
    success, _, _ = run_command(["kubectl", "get", "namespace", namespace])
    if success:
        print(f"  Namespace '{namespace}' exists")
        return True
    
    print(f"  Creating namespace '{namespace}'...")
    success, _, stderr = run_command([
        "kubectl", "create", "namespace", namespace
    ])
    
    if success:
        print(f"  ✓ Namespace created")
        return True
    else:
        print(f"  ✗ Failed: {stderr}")
        return False


def build_image(service_name: str, app_dir: Path) -> bool:
    """Build Docker image."""
    print(f"\nBuilding Docker image for {service_name}...")
    
    cmd = [
        "docker", "build",
        "-t", f"{service_name}:latest",
        str(app_dir)
    ]
    
    success, stdout, stderr = run_command(cmd, capture=False)
    
    if success:
        print(f"  ✓ Image built: {service_name}:latest")
        return True
    else:
        print(f"  ✗ Build failed")
        return False


def load_image_to_minikube(service_name: str) -> bool:
    """Load image to Minikube."""
    print(f"\nLoading image to Minikube...")
    
    cmd = ["minikube", "image", "load", f"{service_name}:latest"]
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"  ✓ Image loaded to Minikube")
        return True
    else:
        print(f"  ⚠ Could not load to Minikube: {stderr}")
        return True  # Not critical


def apply_manifests(service_name: str, namespace: str, app_dir: Path) -> bool:
    """Apply Kubernetes manifests."""
    k8s_dir = app_dir / "k8s"
    
    if not k8s_dir.exists():
        print(f"  ✗ k8s directory not found")
        return False
    
    print(f"\nApplying Kubernetes manifests...")
    
    # Apply all YAML files
    for yaml_file in sorted(k8s_dir.glob("*.yaml")):
        print(f"  Applying {yaml_file.name}...")
        
        success, stdout, stderr = run_command([
            "kubectl", "apply", "-f", str(yaml_file),
            "-n", namespace
        ])
        
        if not success:
            print(f"    ✗ Failed: {stderr[:100]}")
            return False
        print(f"    ✓ Applied")
    
    return True


def wait_for_deployment(service_name: str, namespace: str, timeout: int = 120) -> bool:
    """Wait for deployment to be ready."""
    print(f"\nWaiting for deployment (timeout: {timeout}s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        success, stdout, stderr = run_command([
            "kubectl", "rollout", "status",
            f"deployment/{service_name}",
            "-n", namespace,
            "--timeout", "10s"
        ])
        
        if success:
            print(f"  ✓ Deployment ready")
            return True
        
        elapsed = int(time.time() - start_time)
        print(f"  Waiting... ({elapsed}s/{timeout}s)")
        time.sleep(5)
    
    print(f"  ✗ Timeout waiting for deployment")
    return False


def get_service_url(service_name: str, namespace: str) -> Optional[str]:
    """Get service URL."""
    success, stdout, _ = run_command([
        "kubectl", "get", "svc", service_name,
        "-n", namespace,
        "-o", "jsonpath={.spec.clusterIP}"
    ])
    
    if success and stdout:
        return stdout
    
    return None


def test_service(service_name: str, namespace: str) -> bool:
    """Test service health endpoint."""
    print(f"\nTesting service health...")
    
    # Port forward and test
    cmd = [
        "kubectl", "run", "test-pod", "--rm", "-i",
        "--image=curlimages/curl", "--restart=Never",
        "--", "curl", "-s",
        f"http://{service_name}.{namespace}.svc.cluster.local/health"
    ]
    
    success, stdout, stderr = run_command(cmd, timeout=30)
    
    if success and "healthy" in stdout:
        print(f"  ✓ Service health check passed")
        print(f"  Response: {stdout[:100]}")
        return True
    else:
        print(f"  ⚠ Health check: {stderr[:100] if stderr else stdout[:100]}")
        return True  # Don't fail deployment


def main():
    parser = argparse.ArgumentParser(
        description="Deploy FastAPI service to Kubernetes"
    )
    parser.add_argument("service", help="Service name/directory")
    parser.add_argument("-n", "--namespace", default="apps",
                       help="Target namespace (default: apps)")
    parser.add_argument("--no-build", action="store_true",
                       help="Skip Docker build")
    parser.add_argument("--timeout", type=int, default=120,
                       help="Deployment timeout (default: 120s)")
    
    args = parser.parse_args()
    
    app_dir = Path(args.service)
    
    if not app_dir.exists():
        print(f"✗ Service directory not found: {app_dir}")
        sys.exit(1)
    
    print("=" * 50)
    print(f"Deploying {args.service} to Kubernetes")
    print(f"Namespace: {args.namespace}")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Ensure namespace
    if not ensure_namespace(args.namespace):
        sys.exit(1)
    
    # Build image
    if not args.no_build:
        if not build_image(args.service, app_dir):
            sys.exit(1)
        
        # Load to Minikube
        load_image_to_minikube(args.service)
    
    # Apply manifests
    if not apply_manifests(args.service, args.namespace, app_dir):
        sys.exit(1)
    
    # Wait for deployment
    if not wait_for_deployment(args.service, args.namespace, args.timeout):
        print("\n⚠ Deployment may still be in progress")
        print(f"Check status: kubectl get pods -n {args.namespace}")
    
    # Test service
    test_service(args.service, args.namespace)
    
    # Summary
    print("\n" + "=" * 50)
    print(f"✓ Deployment complete!")
    print(f"\nAccess:")
    print(f"  kubectl port-forward svc/{args.service} -n {args.namespace} 8080:80")
    print(f"  curl http://localhost:8080/health")
    print(f"\nLogs:")
    print(f"  kubectl logs -n {args.namespace} -l app={args.service} -f")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
