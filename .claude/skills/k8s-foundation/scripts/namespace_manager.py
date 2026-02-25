#!/usr/bin/env python3
"""
Namespace Manager - Create, list, delete Kubernetes namespaces

Usage:
    python namespace_manager.py create <name>
    python namespace_manager.py list
    python namespace_manager.py delete <name>
    python namespace_manager.py exists <name>
"""

import subprocess
import json
import sys
from typing import List, Optional


def run_command(cmd: List[str]) -> tuple:
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


def create_namespace(name: str) -> bool:
    """Create a Kubernetes namespace."""
    print(f"Creating namespace: {name}")
    
    # Check if already exists
    exists_success, _, _ = run_command([
        "kubectl", "get", "namespace", name
    ])
    
    if exists_success:
        print(f"  Namespace '{name}' already exists")
        return True
    
    # Create namespace using dry-run and apply
    success, stdout, stderr = run_command([
        "kubectl", "create", "namespace", name,
        "--dry-run=client", "-o", "yaml"
    ])
    
    if not success:
        print(f"  Error preparing namespace: {stderr}")
        # Try direct create
        success, stdout, stderr = run_command([
            "kubectl", "create", "namespace", name
        ])
        if success:
            print(f"✓ Namespace '{name}' created")
            return True
        print(f"  Error: {stderr}")
        return False
    
    # Apply the namespace
    proc = subprocess.Popen(
        ["kubectl", "apply", "-f", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=stdout)
    
    if proc.returncode == 0:
        print(f"✓ Namespace '{name}' created")
        return True
    else:
        print(f"  Error: {stderr}")
        return False


def list_namespaces() -> bool:
    """List all Kubernetes namespaces."""
    print("Listing namespaces...")
    
    success, stdout, stderr = run_command([
        "kubectl", "get", "namespaces", "-o",
        "custom-columns=NAME:.metadata.name,STATUS:.status.phase,AGE:.metadata.creationTimestamp"
    ])
    
    if not success:
        print(f"  Error: {stderr}")
        return False
    
    print(stdout)
    return True


def delete_namespace(name: str, force: bool = False) -> bool:
    """Delete a Kubernetes namespace."""
    print(f"Deleting namespace: {name}")
    
    # Check if exists
    exists_success, _, _ = run_command([
        "kubectl", "get", "namespace", name
    ])
    
    if not exists_success:
        print(f"  Namespace '{name}' does not exist")
        return True
    
    if not force:
        confirm = input(f"  Are you sure you want to delete '{name}'? [y/N]: ")
        if confirm.lower() != 'y':
            print("  Cancelled")
            return True
    
    success, stdout, stderr = run_command([
        "kubectl", "delete", "namespace", name,
        "--timeout=120s"
    ])
    
    if success:
        print(f"✓ Namespace '{name}' deleted")
        return True
    else:
        print(f"  Error: {stderr}")
        return False


def namespace_exists(name: str) -> bool:
    """Check if a namespace exists."""
    success, stdout, stderr = run_command([
        "kubectl", "get", "namespace", name
    ])
    
    if success:
        print(f"✓ Namespace '{name}' exists")
        return True
    else:
        print(f"  Namespace '{name}' does not exist")
        return False


def get_namespace_info(name: str) -> bool:
    """Get detailed information about a namespace."""
    print(f"Getting info for namespace: {name}")
    
    # Get namespace details
    success, stdout, stderr = run_command([
        "kubectl", "get", "namespace", name, "-o", "yaml"
    ])
    
    if not success:
        print(f"  Error: {stderr}")
        return False
    
    print(stdout)
    
    # Get resources in namespace
    print("\nResources in namespace:")
    
    resources = ["pods", "services", "deployments", "statefulsets", "configmaps", "secrets"]
    
    for resource in resources:
        success, stdout, stderr = run_command([
            "kubectl", "get", resource, "-n", name,
            "-o", "custom-columns=NAME:.metadata.name,STATUS:.status.phase"
        ])
        
        if success and stdout.strip():
            print(f"\n{resource.capitalize()}:")
            print(stdout)
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python namespace_manager.py create <name>")
        print("  python namespace_manager.py list")
        print("  python namespace_manager.py delete <name>")
        print("  python namespace_manager.py exists <name>")
        print("  python namespace_manager.py info <name>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Error: Missing namespace name")
            sys.exit(1)
        success = create_namespace(sys.argv[2])
    
    elif command == "list":
        success = list_namespaces()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Missing namespace name")
            sys.exit(1)
        force = "--force" in sys.argv or "-f" in sys.argv
        success = delete_namespace(sys.argv[2], force)
    
    elif command == "exists":
        if len(sys.argv) < 3:
            print("Error: Missing namespace name")
            sys.exit(1)
        success = namespace_exists(sys.argv[2])
    
    elif command == "info":
        if len(sys.argv) < 3:
            print("Error: Missing namespace name")
            sys.exit(1)
        success = get_namespace_info(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        print("\nAvailable commands: create, list, delete, exists, info")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
