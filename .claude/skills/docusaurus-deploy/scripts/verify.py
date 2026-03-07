#!/usr/bin/env python3
"""
Verify Docusaurus Deployment - Check pods, services, and site accessibility

Usage: python verify.py <site-name> --namespace docs
"""

import argparse
import subprocess
import json
import sys
import time
from typing import List, Dict, Optional


def run_command(cmd: list, timeout: int = 30) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def get_pods(namespace: str, label_selector: Optional[str] = None) -> List[Dict]:
    """Get pods in namespace."""
    cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
    if label_selector:
        cmd.extend(["-l", label_selector])
    
    success, stdout, _ = run_command(cmd)
    if not success:
        return []
    
    try:
        data = json.loads(stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def check_pod_status(pod: Dict) -> Dict:
    """Check pod status and return details."""
    name = pod["metadata"]["name"]
    status = pod.get("status", {})
    phase = status.get("phase", "Unknown")
    
    container_statuses = status.get("containerStatuses", [])
    ready_count = sum(1 for cs in container_statuses if cs.get("ready", False))
    total_containers = len(container_statuses)
    
    state_info = []
    for cs in container_statuses:
        state = cs.get("state", {})
        if "waiting" in state:
            reason = state["waiting"].get("reason", "Unknown")
            state_info.append(reason)
        elif "terminated" in state:
            reason = state["terminated"].get("reason", "Unknown")
            state_info.append(reason)
    
    return {
        "name": name,
        "phase": phase,
        "ready": f"{ready_count}/{total_containers}",
        "state": state_info[0] if state_info else "Running",
        "restarts": sum(cs.get("restartCount", 0) for cs in container_statuses)
    }


def get_services(namespace: str) -> List[Dict]:
    """Get services in namespace."""
    cmd = ["kubectl", "get", "services", "-n", namespace, "-o", "json"]
    success, stdout, _ = run_command(cmd)
    
    if not success:
        return []
    
    try:
        data = json.loads(stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def test_site_accessibility(namespace: str, service_name: str) -> bool:
    """Test if site is accessible via port-forward."""
    print("\nTesting site accessibility...")
    
    pods = get_pods(namespace, f"app={service_name}")
    if not pods:
        print("  ✗ No pods found")
        return False
    
    pod_name = pods[0]["metadata"]["name"]
    
    # Test by executing curl inside the pod
    cmd = [
        "kubectl", "exec", "-n", namespace, pod_name, "--",
        "wget", "-q", "-O", "-", "http://localhost:3000/health"
    ]
    
    success, stdout, stderr = run_command(cmd, timeout=10)
    
    if success:
        print(f"  ✓ Site is accessible")
        return True
    else:
        print(f"  ✗ Site not accessible: {stderr[:100]}")
        return False


def verify_deployment(site_name: str, namespace: str) -> bool:
    """Verify Docusaurus deployment is healthy."""
    print("=" * 60)
    print(f"Docusaurus Deployment Verification - {site_name}")
    print("=" * 60)
    
    all_healthy = True
    
    # Check pods
    print("\n📦 Pods:")
    pods = get_pods(namespace, f"app={site_name}")
    
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
    
    # Check services
    print("\n🌐 Services:")
    services = get_services(namespace)
    
    site_services = [s for s in services if site_name in s["metadata"]["name"]]
    
    if not site_services:
        print("  ✗ No services found")
        all_healthy = False
    else:
        for svc in site_services:
            name = svc["metadata"]["name"]
            svc_type = svc["spec"].get("type", "ClusterIP")
            ports = [p["port"] for p in svc["spec"].get("ports", [])]
            print(f"  • {name} ({svc_type}): ports={ports}")
    
    # Test accessibility
    if site_services:
        if not test_site_accessibility(namespace, site_name):
            all_healthy = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_healthy:
        print("✓ Docusaurus deployment is healthy!")
        print(f"\nAccess the site:")
        print(f"  kubectl port-forward svc/{site_name} -n {namespace} 8080:80")
        print(f"  Open http://localhost:8080 in your browser")
    else:
        print("⚠ Docusaurus deployment has issues")
        print("\nDebug commands:")
        print(f"  kubectl describe pods -n {namespace} -l app={site_name}")
        print(f"  kubectl logs -n {namespace} -l app={site_name}")
    
    return all_healthy


def main():
    parser = argparse.ArgumentParser(
        description="Verify Docusaurus deployment on Kubernetes"
    )
    parser.add_argument("site_name", help="Name of the Docusaurus site")
    parser.add_argument(
        "-n", "--namespace",
        default="docs",
        help="Namespace to check (default: docs)"
    )
    
    args = parser.parse_args()
    
    success = verify_deployment(args.site_name, args.namespace)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
