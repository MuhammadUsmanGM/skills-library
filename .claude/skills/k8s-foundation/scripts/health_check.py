#!/usr/bin/env python3
"""
Kubernetes Cluster Health Check

Usage: python health_check.py
"""

import subprocess
import json
import sys
from typing import Dict, List, Tuple


def run_command(cmd: List[str]) -> Tuple[bool, str, str]:
    """Run command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def check_kubectl() -> bool:
    """Check if kubectl is available."""
    success, stdout, stderr = run_command(["kubectl", "version", "--client"])
    if success:
        print("✓ kubectl is installed")
        return True
    print("✗ kubectl not found")
    return False


def check_cluster_connection() -> bool:
    """Check connection to Kubernetes cluster."""
    success, stdout, stderr = run_command(["kubectl", "cluster-info"])
    if success:
        # Extract cluster URL from output
        for line in stdout.split('\n'):
            if 'Kubernetes control plane' in line:
                print(f"✓ Connected to cluster")
                break
        return True
    print("✗ Cannot connect to cluster")
    print(f"  Error: {stderr}")
    return False


def check_nodes() -> Tuple[bool, List[Dict]]:
    """Check node status."""
    success, stdout, stderr = run_command([
        "kubectl", "get", "nodes", "-o", "json"
    ])
    
    if not success:
        print("✗ Failed to get nodes")
        return False, []
    
    try:
        data = json.loads(stdout)
        nodes = data.get("items", [])
        
        all_ready = True
        for node in nodes:
            name = node["metadata"]["name"]
            conditions = node["status"].get("conditions", [])
            
            ready = False
            for cond in conditions:
                if cond["type"] == "Ready":
                    ready = cond["status"] == "True"
                    status_icon = "✓" if ready else "✗"
                    print(f"  {status_icon} Node {name}: {cond['status']}")
                    break
            
            if not ready:
                all_ready = False
        
        if all_ready:
            print(f"✓ All {len(nodes)} node(s) ready")
        
        return all_ready, nodes
        
    except json.JSONDecodeError:
        print("✗ Failed to parse node data")
        return False, []


def check_system_pods() -> bool:
    """Check kube-system pods are running."""
    success, stdout, stderr = run_command([
        "kubectl", "get", "pods", "-n", "kube-system", "-o", "json"
    ])
    
    if not success:
        print("✗ Failed to get system pods")
        return False
    
    try:
        data = json.loads(stdout)
        pods = data.get("items", [])
        
        running = 0
        not_running = 0
        
        for pod in pods:
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase", "Unknown")
            
            if phase == "Running":
                running += 1
            else:
                not_running += 1
                print(f"  ⚠ Pod {name}: {phase}")
        
        print(f"✓ {running} system pods running")
        if not_running > 0:
            print(f"  {not_running} pods not running (may be normal)")
        
        return True
        
    except json.JSONDecodeError:
        print("✗ Failed to parse pod data")
        return False


def check_helm() -> bool:
    """Check if Helm is available."""
    success, stdout, stderr = run_command(["helm", "version"])
    if success:
        # Extract version from output
        for line in stdout.split('\n'):
            if 'version' in line.lower():
                print(f"✓ Helm: {line.strip()}")
                break
        return True
    print("✗ Helm not found")
    return False


def check_storage_class() -> bool:
    """Check if default storage class exists."""
    success, stdout, stderr = run_command([
        "kubectl", "get", "storageclass", "-o", "json"
    ])
    
    if not success:
        print("⚠ Failed to get storage classes (may not be critical)")
        return False
    
    try:
        data = json.loads(stdout)
        classes = data.get("items", [])
        
        default_exists = any(
            sc["metadata"].get("annotations", {}).get("storageclass.kubernetes.io/is-default-class") == "true"
            for sc in classes
        )
        
        if default_exists:
            print("✓ Default storage class exists")
            return True
        elif classes:
            print(f"⚠ No default storage class (found {len(classes)} classes)")
            return True  # Not critical
        else:
            print("⚠ No storage classes found")
            return True  # Not critical for basic operations
            
    except json.JSONDecodeError:
        return False


def main():
    print("=" * 50)
    print("Kubernetes Cluster Health Check")
    print("=" * 50)
    print()
    
    checks = [
        ("kubectl installed", check_kubectl),
        ("cluster connection", check_cluster_connection),
        ("nodes ready", lambda: check_nodes()[0]),
        ("system pods", check_system_pods),
        ("helm installed", check_helm),
        ("storage class", check_storage_class),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        icon = "✓" if result else "✗"
        print(f"  {icon} {name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ Cluster is healthy and ready for deployments")
        sys.exit(0)
    elif passed >= total - 1:
        print("\n⚠ Cluster is mostly healthy, proceed with caution")
        sys.exit(0)
    else:
        print("\n✗ Cluster has issues, fix before deploying")
        sys.exit(1)


if __name__ == "__main__":
    main()
