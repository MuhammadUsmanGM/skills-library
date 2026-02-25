#!/usr/bin/env python3
"""
Verify Kafka Installation - Check pods, services, and connectivity

Usage: python verify.py --namespace kafka
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
    """Check pod status and return details."""
    name = pod["metadata"]["name"]
    status = pod.get("status", {})
    phase = status.get("phase", "Unknown")
    
    # Get container statuses
    container_statuses = status.get("containerStatuses", [])
    ready_count = sum(1 for cs in container_statuses if cs.get("ready", False))
    total_containers = len(container_statuses)
    
    # Get detailed state
    state_info = []
    for cs in container_statuses:
        state = cs.get("state", {})
        if "waiting" in state:
            reason = state["waiting"].get("reason", "Unknown")
            message = state["waiting"].get("message", "")
            state_info.append(f"{reason}: {message[:50]}" if message else reason)
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


def check_kafka_connectivity(namespace: str) -> bool:
    """Test Kafka connectivity using kubectl exec."""
    print("\nTesting Kafka connectivity...")
    
    # Get a Kafka pod
    pods = get_pods(namespace, "app.kubernetes.io/name=kafka")
    if not pods:
        print("  ✗ No Kafka pods found")
        return False
    
    kafka_pod = pods[0]["metadata"]["name"]
    
    # Try to list topics using kafka-topics.sh
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--list"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"  ✓ Can connect to Kafka broker")
        topics = [t for t in stdout.strip().split('\n') if t]
        print(f"  Topics found: {len(topics)}")
        return True
    else:
        print(f"  ✗ Cannot connect to Kafka: {stderr[:100]}")
        return False


def verify_kafka_installation(namespace: str) -> bool:
    """Verify Kafka installation is healthy."""
    print("=" * 60)
    print(f"Kafka Installation Verification - Namespace: {namespace}")
    print("=" * 60)
    
    all_healthy = True
    
    # Check Kafka pods
    print("\n📦 Kafka Pods:")
    kafka_pods = get_pods(namespace, "app.kubernetes.io/name=kafka")
    
    if not kafka_pods:
        print("  ✗ No Kafka pods found")
        all_healthy = False
    else:
        for pod in kafka_pods:
            status = check_pod_status(pod)
            icon = "✓" if status["phase"] == "Running" else "⚠"
            print(f"  {icon} {status['name']}: {status['phase']} "
                  f"(ready: {status['ready']}, restarts: {status['restarts']})")
            if status["phase"] != "Running":
                all_healthy = False
    
    # Check Zookeeper pods
    print("\n📦 Zookeeper Pods:")
    zookeeper_pods = get_pods(namespace, "app.kubernetes.io/name=zookeeper")
    
    if not zookeeper_pods:
        print("  ✗ No Zookeeper pods found")
        all_healthy = False
    else:
        for pod in zookeeper_pods:
            status = check_pod_status(pod)
            icon = "✓" if status["phase"] == "Running" else "⚠"
            print(f"  {icon} {status['name']}: {status['phase']} "
                  f"(ready: {status['ready']}, restarts: {status['restarts']})")
            if status["phase"] != "Running":
                all_healthy = False
    
    # Check services
    print("\n🌐 Services:")
    services = get_services(namespace)
    
    if not services:
        print("  ✗ No services found")
        all_healthy = False
    else:
        for svc in services:
            name = svc["metadata"]["name"]
            svc_type = svc["spec"].get("type", "ClusterIP")
            cluster_ip = svc["spec"].get("clusterIP", "None")
            ports = [p["port"] for p in svc["spec"].get("ports", [])]
            print(f"  • {name} ({svc_type}): {cluster_ip} ports={ports}")
    
    # Test connectivity
    if kafka_pods:
        if not check_kafka_connectivity(namespace):
            all_healthy = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_healthy:
        print("✓ Kafka installation is healthy!")
        print("\nUsage:")
        print(f"  kubectl port-forward svc/kafka -n {namespace} 9092:9092")
        print("  Bootstrap server: localhost:9092")
    else:
        print("⚠ Kafka installation has issues")
        print("\nDebug commands:")
        print(f"  kubectl describe pods -n {namespace}")
        print(f"  kubectl logs -n {namespace} -l app.kubernetes.io/name=kafka")
    
    return all_healthy


def main():
    parser = argparse.ArgumentParser(
        description="Verify Kafka installation on Kubernetes"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="kafka",
        help="Namespace to check (default: kafka)"
    )
    
    args = parser.parse_args()
    
    success = verify_kafka_installation(args.namespace)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
