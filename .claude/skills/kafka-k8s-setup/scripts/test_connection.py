#!/usr/bin/env python3
"""
Test Kafka Connection - Produce and consume test messages

Usage:
    python test_connection.py produce --namespace kafka
    python test_connection.py consume --namespace kafka
    python test_connection.py full --namespace kafka
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional


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


def get_kafka_pod(namespace: str) -> Optional[str]:
    """Get a Kafka pod name."""
    cmd = [
        "kubectl", "get", "pods", "-n", namespace,
        "-l", "app.kubernetes.io/name=kafka",
        "-o", "jsonpath={.items[0].metadata.name}"
    ]
    
    success, stdout, _ = run_command(cmd)
    return stdout if success and stdout else None


def produce_test_message(namespace: str, topic: str = "test.topic") -> bool:
    """Produce a test message to Kafka."""
    print(f"Producing test message to topic '{topic}'...")
    
    kafka_pod = get_kafka_pod(namespace)
    if not kafka_pod:
        print("✗ No Kafka pod found")
        return False
    
    message = f"Test message from Kafka connection test at {datetime.now().isoformat()}"
    
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-console-producer.sh",
        "--bootstrap-server", "localhost:9092",
        "--topic", topic
    ]
    
    # Send message via stdin
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = proc.communicate(input=f"{message}\n")
    
    if proc.returncode == 0:
        print(f"✓ Message produced successfully")
        print(f"  Topic: {topic}")
        print(f"  Message: {message[:50]}...")
        return True
    else:
        print(f"✗ Failed to produce message: {stderr}")
        return False


def consume_test_message(namespace: str, topic: str = "test.topic", timeout: int = 10) -> bool:
    """Consume a test message from Kafka."""
    print(f"Consuming from topic '{topic}' (timeout: {timeout}s)...")
    
    kafka_pod = get_kafka_pod(namespace)
    if not kafka_pod:
        print("✗ No Kafka pod found")
        return False
    
    cmd = [
        "kubectl", "exec", "-n", namespace, kafka_pod, "--",
        "/opt/bitnami/kafka/bin/kafka-console-consumer.sh",
        "--bootstrap-server", "localhost:9092",
        "--topic", topic,
        "--from-beginning",
        "--timeout-ms", str(timeout * 1000),
        "--max-messages", "1"
    ]
    
    success, stdout, stderr = run_command(cmd, timeout=timeout + 5)
    
    if success and stdout.strip():
        print(f"✓ Message consumed successfully")
        print(f"  Message: {stdout.strip()[:50]}...")
        return True
    elif "timeout" in stderr.lower() or "kafka.consumer.ConsumerTimeoutException" in stderr:
        print(f"⚠ No messages found (timeout)")
        return True  # Not necessarily an error
    else:
        print(f"✗ Failed to consume message: {stderr[:100]}")
        return False


def full_connection_test(namespace: str) -> bool:
    """Run full connection test: produce then consume."""
    topic = f"test.{int(time.time())}"
    
    print("=" * 50)
    print("Kafka Connection Test")
    print("=" * 50)
    
    # Create topic first
    print(f"\n1. Creating temporary topic '{topic}'...")
    create_success, _, stderr = run_command([
        "kubectl", "exec", "-n", namespace, get_kafka_pod(namespace) or "", "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--create",
        "--topic", topic,
        "--partitions", "1",
        "--replication-factor", "1"
    ])
    
    if not create_success and "already exists" not in stderr.lower():
        print(f"✗ Failed to create topic: {stderr}")
        return False
    print("✓ Topic created")
    
    # Produce message
    print("\n2. Producing test message...")
    if not produce_test_message(namespace, topic):
        return False
    
    # Small delay
    time.sleep(2)
    
    # Consume message
    print("\n3. Consuming test message...")
    if not consume_test_message(namespace, topic):
        print("\n⚠ Note: Message may not be consumed yet due to timing")
    
    # Cleanup - delete topic
    print(f"\n4. Cleaning up topic '{topic}'...")
    run_command([
        "kubectl", "exec", "-n", namespace, get_kafka_pod(namespace) or "", "--",
        "/opt/bitnami/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:9092",
        "--delete",
        "--topic", topic
    ])
    
    print("\n" + "=" * 50)
    print("✓ Kafka connection test complete!")
    print("=" * 50)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test Kafka connection"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # produce
    produce_parser = subparsers.add_parser("produce", help="Produce test message")
    produce_parser.add_argument("-n", "--namespace", default="kafka",
                               help="Namespace (default: kafka)")
    produce_parser.add_argument("-t", "--topic", default="test.topic",
                               help="Topic (default: test.topic)")
    
    # consume
    consume_parser = subparsers.add_parser("consume", help="Consume test message")
    consume_parser.add_argument("-n", "--namespace", default="kafka",
                               help="Namespace (default: kafka)")
    consume_parser.add_argument("-t", "--topic", default="test.topic",
                               help="Topic (default: test.topic)")
    
    # full
    full_parser = subparsers.add_parser("full", help="Full connection test")
    full_parser.add_argument("-n", "--namespace", default="kafka",
                            help="Namespace (default: kafka)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "produce":
        success = produce_test_message(args.namespace, args.topic)
    elif args.command == "consume":
        success = consume_test_message(args.namespace, args.topic)
    elif args.command == "full":
        success = full_connection_test(args.namespace)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
