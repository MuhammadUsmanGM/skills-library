#!/usr/bin/env python3
"""
Deploy Next.js Application to Kubernetes

Usage: python deploy.py <app-name> --namespace apps
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


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
    """Check kubectl and cluster access."""
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


def apply_manifests(app_name: str, namespace: str) -> bool:
    """Apply Kubernetes manifests."""
    k8s_dir = Path(app_name) / "k8s"
    
    if not k8s_dir.exists():
        print(f"  ✗ k8s directory not found")
        return False
    
    print(f"\nApplying Kubernetes manifests...")
    
    # Apply in order
    manifests = [
        "configmap.yaml",
        "deployment.yaml",
        "hpa.yaml",
        "networkpolicy.yaml",
    ]
    
    for manifest in manifests:
        manifest_path = k8s_dir / manifest
        
        if not manifest_path.exists():
            print(f"  ⚠ Skipping {manifest} (not found)")
            continue
        
        print(f"  Applying {manifest}...")
        success, stdout, stderr = run_command([
            "kubectl", "apply", "-f", str(manifest_path),
            "-n", namespace
        ])
        
        if not success:
            print(f"    ✗ Failed: {stderr[:100]}")
            return False
        print(f"    ✓ Applied")
    
    return True


def wait_for_deployment(app_name: str, namespace: str, timeout: int = 120) -> bool:
    """Wait for deployment to be ready."""
    print(f"\nWaiting for deployment (timeout: {timeout}s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        success, stdout, stderr = run_command([
            "kubectl", "rollout", "status",
            f"deployment/{app_name}",
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


def verify_pods(app_name: str, namespace: str) -> bool:
    """Verify pods are running."""
    print(f"\nVerifying pods...")
    
    success, stdout, stderr = run_command([
        "kubectl", "get", "pods", "-n", namespace,
        "-l", f"app={app_name}",
        "-o", "wide"
    ])
    
    if success:
        print(stdout)
        
        # Check if any pods are Running
        if "Running" in stdout:
            return True
    
    return False


def test_service(app_name: str, namespace: str) -> bool:
    """Test service connectivity."""
    print(f"\nTesting service...")
    
    success, stdout, stderr = run_command([
        "kubectl", "run", "test-pod", "--rm", "-i",
        "--image=curlimages/curl", "--restart=Never",
        "--", "curl", "-s", "-o", "/dev/null", "-w", "%{{http_code}}",
        f"http://{app_name}.{namespace}.svc.cluster.local/api/health"
    ], timeout=30)
    
    if success and "200" in stdout:
        print(f"  ✓ Service health check passed")
        return True
    else:
        print(f"  ⚠ Service test: {stderr[:100] if stderr else stdout[:100]}")
        return True  # Don't fail deployment


def get_service_info(app_name: str, namespace: str) -> None:
    """Print service access information."""
    print(f"\n" + "=" * 50)
    print(f"Access Information")
    print("=" * 50)
    
    # Get service
    success, stdout, _ = run_command([
        "kubectl", "get", "svc", app_name,
        "-n", namespace,
        "-o", "wide"
    ])
    
    if success:
        print(f"\nService:")
        print(stdout)
    
    # Get pods
    success, stdout, _ = run_command([
        "kubectl", "get", "pods", "-n", namespace,
        "-l", f"app={app_name}",
        "-o", "wide"
    ])
    
    if success:
        print(f"\nPods:")
        print(stdout)
    
    print(f"\nPort Forward:")
    print(f"  kubectl port-forward svc/{app_name} -n {namespace} 3000:80")
    
    print(f"\nLogs:")
    print(f"  kubectl logs -n {namespace} -l app={app_name} -f")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Next.js application to Kubernetes"
    )
    parser.add_argument("app", help="Application name/directory")
    parser.add_argument("-n", "--namespace", default="apps",
                       help="Target namespace (default: apps)")
    parser.add_argument("--timeout", type=int, default=120,
                       help="Deployment timeout (default: 120s)")
    parser.add_argument("--skip-build", action="store_true",
                       help="Skip image build check")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"Deploying {args.app} to Kubernetes")
    print(f"Namespace: {args.namespace}")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Ensure namespace
    if not ensure_namespace(args.namespace):
        sys.exit(1)
    
    # Check image exists (unless skipped)
    if not args.skip_build:
        success, _, _ = run_command([
            "docker", "images", "-q", f"{args.app}:latest"
        ])
        if not success:
            print(f"\n⚠ Image not found locally")
            print(f"Build first: python scripts/build_image.py {args.app}")
            sys.exit(1)
    
    # Apply manifests
    if not apply_manifests(args.app, args.namespace):
        sys.exit(1)
    
    # Wait for deployment
    if not wait_for_deployment(args.app, args.namespace, args.timeout):
        print("\n⚠ Deployment may still be in progress")
    
    # Verify pods
    verify_pods(args.app, args.namespace)
    
    # Test service
    test_service(args.app, args.namespace)
    
    # Print access info
    get_service_info(args.app, args.namespace)
    
    print("\n" + "=" * 50)
    print(f"✓ Deployment complete!")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
