#!/usr/bin/env python3
"""
Kafka Topic Manager - Create, list, delete topics

Usage:
    python topic_manager.py list --namespace kafka
    python topic_manager.py create <topic> --partitions 3 --replicas 1
    python topic_manager.py delete <topic>
    python topic_manager.py describe <topic>
"""

import argparse
import subprocess
import json
import sys
from typing import List, Optional


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


def get_kafka_pod(namespace: str) -> Optional[str]:
    """Get a Kafka pod name for executing commands."""
    cmd = [
        "kubectl", "get", "pods", "-n", namespace,
        "-l", "app.kubernetes.io/name=kafka",
        "-o", "jsonpath={.items[0].metadata.name}"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success and stdout:
        return stdout
    return None


def list_topics(namespace: str) -> bool:
    """List all Kafka topics."""
    print(f"Listing topics in namespace '{namespace}'...")
    
    kafka_pod = get_kafka_pod(namespace)
    if not kafka_pod:
        print("✗ No Kafka pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--list"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        topics = [t for t in stdout.strip().split('\n') if t]
        print(f"\nTopics ({len(topics)}):")
        for topic in topics:
            print(f"  • {topic}")
        return True
    else:
        print(f"✗ Failed to list topics: {stderr}")
        return False


def create_topic(
    namespace: str,
    topic: str,
    partitions: int = 3,
    replicas: int = 1
) -> bool:
    """Create a Kafka topic."""
    print(f"Creating topic '{topic}'...")
    
    kafka_pod = get_kafka_pod(namespace)
    if not kafka_pod:
        print("✗ No Kafka pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--create",
        "--topic", topic,
        "--partitions", str(partitions),
        "--replication-factor", str(replicas)
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✓ Topic '{topic}' created")
        print(f"  Partitions: {partitions}, Replicas: {replicas}")
        return True
    else:
        # Check if topic already exists
        if "already exists" in stderr.lower():
            print(f"  Topic '{topic}' already exists")
            return True
        print(f"✗ Failed to create topic: {stderr}")
        return False


def delete_topic(namespace: str, topic: str) -> bool:
    """Delete a Kafka topic."""
    print(f"Deleting topic '{topic}'...")
    
    kafka_pod = get_kafka_pod(namespace)
    if not kafka_pod:
        print("✗ No Kafka pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--delete",
        "--topic", topic
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✓ Topic '{topic}' deleted")
        return True
    else:
        print(f"✗ Failed to delete topic: {stderr}")
        return False


def describe_topic(namespace: str, topic: str) -> bool:
    """Describe a Kafka topic."""
    print(f"Describing topic '{topic}'...")
    
    kafka_pod = get_kafka_pod(namespace)
    if not kafka_pod:
        print("✗ No Kafka pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--describe",
        "--topic", topic
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"\n{stdout}")
        return True
    else:
        print(f"✗ Failed to describe topic: {stderr}")
        return False


def create_learnflow_topics(namespace: str) -> bool:
    """Create standard LearnFlow topics."""
    topics = [
        ("learning.events", 3, 1),
        ("code.submissions", 3, 1),
        ("exercise.completions", 3, 1),
        ("struggle.alerts", 3, 1),
        ("progress.updates", 3, 1),
    ]
    
    print(f"Creating LearnFlow topics in namespace '{namespace}'...")
    
    all_success = True
    for topic, partitions, replicas in topics:
        if not create_topic(namespace, topic, partitions, replicas):
            all_success = False
    
    if all_success:
        print(f"\n✓ Created {len(topics)} LearnFlow topics")
    
    return all_success


def main():
    parser = argparse.ArgumentParser(
        description="Kafka Topic Manager"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # list
    list_parser = subparsers.add_parser("list", help="List topics")
    list_parser.add_argument("-n", "--namespace", default="kafka",
                            help="Namespace (default: kafka)")
    
    # create
    create_parser = subparsers.add_parser("create", help="Create a topic")
    create_parser.add_argument("topic", help="Topic name")
    create_parser.add_argument("-n", "--namespace", default="kafka",
                              help="Namespace (default: kafka)")
    create_parser.add_argument("-p", "--partitions", type=int, default=3,
                              help="Number of partitions (default: 3)")
    create_parser.add_argument("-r", "--replicas", type=int, default=1,
                              help="Replication factor (default: 1)")
    
    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a topic")
    delete_parser.add_argument("topic", help="Topic name")
    delete_parser.add_argument("-n", "--namespace", default="kafka",
                              help="Namespace (default: kafka)")
    
    # describe
    describe_parser = subparsers.add_parser("describe", help="Describe a topic")
    describe_parser.add_argument("topic", help="Topic name")
    describe_parser.add_argument("-n", "--namespace", default="kafka",
                                help="Namespace (default: kafka)")
    
    # create-learnflow-topics
    learnflow_parser = subparsers.add_parser("create-learnflow-topics",
                                             help="Create LearnFlow topics")
    learnflow_parser.add_argument("-n", "--namespace", default="kafka",
                                  help="Namespace (default: kafka)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "list":
        success = list_topics(args.namespace)
    elif args.command == "create":
        success = create_topic(
            args.namespace, args.topic,
            args.partitions, args.replicas
        )
    elif args.command == "delete":
        success = delete_topic(args.namespace, args.topic)
    elif args.command == "describe":
        success = describe_topic(args.namespace, args.topic)
    elif args.command == "create-learnflow-topics":
        success = create_learnflow_topics(args.namespace)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
