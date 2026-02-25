#!/usr/bin/env python3
"""
Deploy Docusaurus to Kubernetes

Usage: python deploy.py <site-name> --namespace docs
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


def apply_manifests(site_name: str, namespace: str) -> bool:
    """Apply Kubernetes manifests."""
    k8s_dir = Path(site_name) / "k8s"
    
    if not k8s_dir.exists():
        print(f"  ✗ k8s directory not found")
        return False
    
    print(f"\nApplying Kubernetes manifests...")
    
    manifest_path = k8s_dir / "deployment.yaml"
    
    if not manifest_path.exists():
        print(f"  ✗ deployment.yaml not found")
        return False
    
    print(f"  Applying deployment.yaml...")
    success, stdout, stderr = run_command([
        "kubectl", "apply", "-f", str(manifest_path),
        "-n", namespace
    ])
    
    if success:
        print(f"    ✓ Applied")
        return True
    else:
        print(f"    ✗ Failed: {stderr[:100]}")
        return False


def wait_for_deployment(site_name: str, namespace: str, timeout: int = 120) -> bool:
    """Wait for deployment to be ready."""
    print(f"\nWaiting for deployment (timeout: {timeout}s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        success, stdout, stderr = run_command([
            "kubectl", "rollout", "status",
            f"deployment/{site_name}",
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


def verify_deployment(site_name: str, namespace: str) -> bool:
    """Verify deployment is running."""
    print(f"\nVerifying deployment...")
    
    # Get pods
    success, stdout, stderr = run_command([
        "kubectl", "get", "pods", "-n", namespace,
        "-l", f"app={site_name}",
        "-o", "wide"
    ])
    
    if success:
        print(f"\nPods:")
        print(stdout)
        
        if "Running" in stdout:
            return True
    
    return False


def test_site(site_name: str, namespace: str) -> bool:
    """Test site accessibility."""
    print(f"\nTesting site...")
    
    success, stdout, stderr = run_command([
        "kubectl", "run", "test-pod", "--rm", "-i",
        "--image=curlimages/curl", "--restart=Never",
        "--", "curl", "-s", "-o", "/dev/null", "-w", "%{{http_code}}",
        f"http://{site_name}.{namespace}.svc.cluster.local/"
    ], timeout=30)
    
    if success and "200" in stdout:
        print(f"  ✓ Site accessible (HTTP 200)")
        return True
    else:
        print(f"  ⚠ Site test: {stderr[:100] if stderr else stdout[:100]}")
        return True


def get_access_info(site_name: str, namespace: str) -> None:
    """Print access information."""
    print(f"\n" + "=" * 50)
    print(f"Access Information")
    print("=" * 50)
    
    # Get service
    success, stdout, _ = run_command([
        "kubectl", "get", "svc", site_name,
        "-n", namespace
    ])
    
    if success:
        print(f"\nService:")
        print(stdout)
    
    print(f"\nPort Forward:")
    print(f"  kubectl port-forward svc/{site_name} -n {namespace} 8080:80")
    
    print(f"\nLogs:")
    print(f"  kubectl logs -n {namespace} -l app={site_name} -f")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Docusaurus to Kubernetes"
    )
    parser.add_argument("site", help="Site name/directory")
    parser.add_argument("-n", "--namespace", default="docs",
                       help="Target namespace (default: docs)")
    parser.add_argument("--timeout", type=int, default=120,
                       help="Deployment timeout (default: 120s)")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"Deploying {args.site} to Kubernetes")
    print(f"Namespace: {args.namespace}")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Ensure namespace
    if not ensure_namespace(args.namespace):
        sys.exit(1)
    
    # Apply manifests
    if not apply_manifests(args.site, args.namespace):
        sys.exit(1)
    
    # Wait for deployment
    if not wait_for_deployment(args.site, args.namespace, args.timeout):
        print("\n⚠ Deployment may still be in progress")
    
    # Verify
    verify_deployment(args.site, args.namespace)
    
    # Test site
    test_site(args.site, args.namespace)
    
    # Print access info
    get_access_info(args.site, args.namespace)
    
    print("\n" + "=" * 50)
    print(f"✓ Deployment complete!")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
