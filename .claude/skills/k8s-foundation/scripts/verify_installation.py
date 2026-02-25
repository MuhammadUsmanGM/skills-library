#!/usr/bin/env python3
"""
Verify Helm Installation - Check if all resources are ready

Usage: python verify_installation.py <release-name> <namespace>
"""

import subprocess
import json
import sys
import time
from typing import List, Dict, Optional


def run_command(cmd: List[str]) -> tuple:
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


def get_release_status(name: str, namespace: str) -> Optional[Dict]:
    """Get Helm release status."""
    success, stdout, stderr = run_command([
        "helm", "status", name,
        "--namespace", namespace,
        "-o", "json"
    ])
    
    if not success:
        return None
    
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def get_pods(namespace: str, labels: Optional[str] = None) -> List[Dict]:
    """Get pods in namespace."""
    cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
    
    if labels:
        cmd.extend(["-l", labels])
    
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        return []
    
    try:
        data = json.loads(stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def check_pod_ready(pod: Dict) -> tuple:
    """Check if pod is ready. Returns (is_ready, phase, message)."""
    name = pod["metadata"]["name"]
    status = pod.get("status", {})
    phase = status.get("phase", "Unknown")
    
    # Check conditions
    ready = False
    message = ""
    
    for condition in status.get("conditions", []):
        if condition["type"] == "Ready":
            ready = condition["status"] == "True"
            if not ready:
                message = condition.get("message", "")
            break
    
    # If pod is in Pending phase, check why
    if phase == "Pending":
        for container_status in status.get("containerStatuses", []):
            waiting = container_status.get("state", {}).get("waiting", {})
            if waiting:
                message = f"{waiting.get('reason', '')}: {waiting.get('message', '')}"
                break
    
    return ready, phase, message


def get_services(namespace: str, labels: Optional[str] = None) -> List[Dict]:
    """Get services in namespace."""
    cmd = ["kubectl", "get", "services", "-n", namespace, "-o", "json"]
    
    if labels:
        cmd.extend(["-l", labels])
    
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        return []
    
    try:
        data = json.loads(stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def verify_installation(
    release_name: str,
    namespace: str,
    timeout: int = 300,
    poll_interval: int = 10
) -> bool:
    """
    Verify Helm installation is complete.
    
    Args:
        release_name: Helm release name
        namespace: Kubernetes namespace
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
    """
    print(f"Verifying installation: {release_name} in {namespace}")
    print(f"Timeout: {timeout}s, Poll interval: {poll_interval}s")
    print("-" * 50)
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Get pods
        pods = get_pods(namespace)
        
        if not pods:
            print(f"\n⚠ No pods found in namespace '{namespace}'")
            print("  Waiting for resources to be created...")
            time.sleep(poll_interval)
            continue
        
        total_pods = len(pods)
        ready_pods = 0
        pending_pods = []
        failed_pods = []
        
        for pod in pods:
            name = pod["metadata"]["name"]
            is_ready, phase, message = check_pod_ready(pod)
            
            if is_ready:
                ready_pods += 1
            elif phase == "Failed":
                failed_pods.append((name, message))
            elif phase in ["Pending", "ContainerCreating"]:
                pending_pods.append((name, phase, message))
            else:
                pending_pods.append((name, phase, message))
        
        print(f"\nPods: {ready_pods}/{total_pods} ready")
        
        if pending_pods:
            print("\nPending/Creating:")
            for name, phase, msg in pending_pods[:5]:  # Show first 5
                print(f"  ⏳ {name}: {phase}")
                if msg:
                    print(f"     → {msg[:100]}")
        
        if failed_pods:
            print("\nFailed:")
            for name, msg in failed_pods:
                print(f"  ✗ {name}: {msg[:100]}")
        
        # Check if all pods are ready
        if ready_pods == total_pods and total_pods > 0:
            print("\n" + "=" * 50)
            print(f"✓ All {total_pods} pods are ready!")
            
            # Get services
            services = get_services(namespace)
            if services:
                print(f"\nServices ({len(services)}):")
                for svc in services:
                    name = svc["metadata"]["name"]
                    svc_type = svc["spec"].get("type", "ClusterIP")
                    cluster_ip = svc["spec"].get("clusterIP", "None")
                    ports = [p["port"] for p in svc["spec"].get("ports", [])]
                    print(f"  • {name} ({svc_type}): {cluster_ip} ports={ports}")
            
            return True
        
        # Check for failed pods
        if failed_pods:
            print("\n⚠ Some pods failed. Check logs with:")
            for name, _ in failed_pods:
                print(f"  kubectl logs -n {namespace} {name}")
        
        elapsed = int(time.time() - start_time)
        print(f"\n⏱ Waiting... ({elapsed}s/{timeout}s)")
        time.sleep(poll_interval)
    
    print("\n" + "=" * 50)
    print(f"✗ Timeout waiting for installation to complete")
    print(f"\nDebug commands:")
    print(f"  kubectl get pods -n {namespace}")
    print(f"  kubectl describe pods -n {namespace}")
    print(f"  kubectl logs -n {namespace} <pod-name>")
    
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_installation.py <release-name> <namespace>")
        print("\nExample:")
        print("  python verify_installation.py kafka kafka")
        sys.exit(1)
    
    release_name = sys.argv[1]
    namespace = sys.argv[2]
    
    # Optional timeout
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    
    success = verify_installation(release_name, namespace, timeout)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
