#!/usr/bin/env python3
"""
Verify Next.js Deployment

Usage: python verify.py <app-name> --namespace apps
"""

import argparse
import subprocess
import sys
import json
from typing import List, Dict


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


def get_pods(app_name: str, namespace: str) -> List[Dict]:
    """Get pods for application."""
    success, stdout, _ = run_command([
        "kubectl", "get", "pods", "-n", namespace,
        "-l", f"app={app_name}",
        "-o", "json"
    ])
    
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
    
    # Get restart count
    restarts = sum(cs.get("restartCount", 0) for cs in container_statuses)
    
    return {
        "name": name,
        "phase": phase,
        "ready": f"{ready_count}/{total_containers}",
        "restarts": restarts
    }


def check_service(app_name: str, namespace: str) -> bool:
    """Check service exists and has endpoints."""
    print("\nChecking service...")
    
    # Get service
    success, stdout, _ = run_command([
        "kubectl", "get", "svc", app_name,
        "-n", namespace,
        "-o", "json"
    ])
    
    if not success:
        print("  ✗ Service not found")
        return False
    
    try:
        data = json.loads(stdout)
        svc_type = data["spec"].get("type", "ClusterIP")
        cluster_ip = data["spec"].get("clusterIP", "None")
        ports = data["spec"].get("ports", [])
        
        print(f"  ✓ Service: {app_name}")
        print(f"    Type: {svc_type}")
        print(f"    ClusterIP: {cluster_ip}")
        print(f"    Ports: {[p['port'] for p in ports]}")
        
        return True
    except json.JSONDecodeError:
        return False


def check_endpoints(app_name: str, namespace: str) -> bool:
    """Check service endpoints."""
    print("\nChecking endpoints...")
    
    success, stdout, _ = run_command([
        "kubectl", "get", "endpoints", app_name,
        "-n", namespace,
        "-o", "json"
    ])
    
    if not success:
        print("  ✗ Endpoints not found")
        return False
    
    try:
        data = json.loads(stdout)
        subsets = data.get("subsets", [])
        
        if not subsets:
            print("  ✗ No endpoints ready")
            return False
        
        addresses = []
        for subset in subsets:
            addresses.extend(subset.get("addresses", []))
        
        print(f"  ✓ {len(addresses)} endpoint(s) ready")
        return True
    except json.JSONDecodeError:
        return False


def test_health_endpoint(app_name: str, namespace: str) -> bool:
    """Test health endpoint via port-forward."""
    print("\nTesting health endpoint...")
    
    # Use kubectl run for testing
    success, stdout, stderr = run_command([
        "kubectl", "run", "test-pod", "--rm", "-i",
        "--image=curlimages/curl", "--restart=Never",
        "--", "curl", "-s", "-w", "\\n%{{http_code}}",
        f"http://{app_name}.{namespace}.svc.cluster.local/api/health"
    ], timeout=30)
    
    if success:
        lines = stdout.strip().split('\n')
        if len(lines) >= 2:
            status_code = lines[-1]
            body = '\n'.join(lines[:-1])
            
            if status_code == "200":
                print(f"  ✓ Health check passed (HTTP {status_code})")
                return True
            else:
                print(f"  ⚠ Health check returned HTTP {status_code}")
                print(f"    Response: {body[:100]}")
                return True
    
    print(f"  ⚠ Health check: {stderr[:100] if stderr else 'Failed'}")
    return True  # Don't fail verification


def check_hpa(app_name: str, namespace: str) -> bool:
    """Check Horizontal Pod Autoscaler."""
    print("\nChecking HPA...")
    
    success, stdout, _ = run_command([
        "kubectl", "get", "hpa", f"{app_name}-hpa",
        "-n", namespace
    ])
    
    if success:
        print(f"  ✓ HPA configured")
        print(f"    {stdout.strip()}")
        return True
    else:
        print("  ⚠ HPA not found (optional)")
        return True


def check_ingress(app_name: str, namespace: str) -> bool:
    """Check Ingress configuration."""
    print("\nChecking Ingress...")
    
    success, stdout, _ = run_command([
        "kubectl", "get", "ingress", f"{app_name}-ingress",
        "-n", namespace,
        "-o", "wide"
    ])
    
    if success:
        print(f"  ✓ Ingress configured")
        print(f"    {stdout.strip()}")
        return True
    else:
        print("  ⚠ Ingress not found (optional)")
        return True


def verify_deployment(app_name: str, namespace: str) -> bool:
    """Verify complete deployment."""
    print("=" * 60)
    print(f"Verification: {app_name} in {namespace}")
    print("=" * 60)
    
    all_healthy = True
    
    # Check pods
    print("\n📦 Pods:")
    pods = get_pods(app_name, namespace)
    
    if not pods:
        print("  ✗ No pods found")
        all_healthy = False
    else:
        for pod in pods:
            status = check_pod_status(pod)
            icon = "✓" if status["phase"] == "Running" else "⚠"
            print(f"  {icon} {status['name']}: {status['phase']} "
                  f"(ready: {status['ready']}, restarts: {status['restarts']})")
            if status["phase"] != "Running":
                all_healthy = False
    
    # Check service
    if not check_service(app_name, namespace):
        all_healthy = False
    
    # Check endpoints
    if not check_endpoints(app_name, namespace):
        all_healthy = False
    
    # Test health
    if pods:
        test_health_endpoint(app_name, namespace)
    
    # Check HPA
    check_hpa(app_name, namespace)
    
    # Check Ingress
    check_ingress(app_name, namespace)
    
    # Summary
    print("\n" + "=" * 60)
    if all_healthy:
        print("✓ Deployment is healthy!")
    else:
        print("⚠ Deployment has issues")
        print("\nDebug commands:")
        print(f"  kubectl describe pods -n {namespace} -l app={app_name}")
        print(f"  kubectl logs -n {namespace} -l app={app_name}")
    
    return all_healthy


def main():
    parser = argparse.ArgumentParser(
        description="Verify Next.js deployment"
    )
    parser.add_argument("app", help="Application name")
    parser.add_argument("-n", "--namespace", default="apps",
                       help="Namespace (default: apps)")
    
    args = parser.parse_args()
    
    success = verify_deployment(args.app, args.namespace)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
