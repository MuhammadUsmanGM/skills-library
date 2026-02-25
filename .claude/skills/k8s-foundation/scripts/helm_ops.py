#!/usr/bin/env python3
"""
Helm Operations - Add repos, update, install, uninstall charts

Usage:
    python helm_ops.py add-repo <name> <url>
    python helm_ops.py update
    python helm_ops.py install <chart> <name> [--namespace <ns>] [--set key=value]
    python helm_ops.py uninstall <name> [--namespace <ns>]
    python helm_ops.py list [--namespace <ns>]
    python helm_ops.py status <name> [--namespace <ns>]
"""

import subprocess
import sys
import argparse
from typing import List, Optional


def run_command(cmd: List[str], capture: bool = True) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    print(f"  Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=120
        )
        if capture:
            return result.returncode == 0, result.stdout, result.stderr
        return result.returncode == 0, "", result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def add_repo(name: str, url: str) -> bool:
    """Add a Helm repository."""
    print(f"Adding Helm repository: {name}")
    success, stdout, stderr = run_command([
        "helm", "repo", "add", name, url
    ])
    
    if success:
        print(f"✓ Repository '{name}' added successfully")
        # Update repos after adding
        update_repos()
        return True
    else:
        print(f"✗ Failed to add repository: {stderr}")
        # Check if already exists
        if "already exists" in stderr.lower():
            print("  Repository already exists, updating...")
            return update_repos()
        return False


def update_repos() -> bool:
    """Update all Helm repositories."""
    print("Updating Helm repositories...")
    success, stdout, stderr = run_command(["helm", "repo", "update"])
    
    if success:
        print("✓ Repositories updated")
        return True
    else:
        print(f"✗ Failed to update repositories: {stderr}")
        return False


def install_chart(
    chart: str,
    name: str,
    namespace: Optional[str] = None,
    settings: Optional[List[str]] = None,
    wait: bool = True
) -> bool:
    """Install a Helm chart."""
    print(f"Installing Helm chart: {chart} as {name}")
    
    cmd = ["helm", "install", name, chart]
    
    if namespace:
        cmd.extend(["--namespace", namespace])
        # Create namespace if not exists
        create_namespace(namespace)
    
    if settings:
        for setting in settings:
            cmd.extend(["--set", setting])
    
    if wait:
        cmd.extend(["--wait", "--timeout", "5m0s"])
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✓ Chart '{name}' installed successfully")
        if stdout:
            print(stdout)
        return True
    else:
        print(f"✗ Failed to install chart: {stderr}")
        return False


def uninstall_chart(name: str, namespace: Optional[str] = None) -> bool:
    """Uninstall a Helm chart."""
    print(f"Uninstalling Helm chart: {name}")
    
    cmd = ["helm", "uninstall", name]
    
    if namespace:
        cmd.extend(["--namespace", namespace])
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✓ Chart '{name}' uninstalled successfully")
        return True
    else:
        print(f"✗ Failed to uninstall chart: {stderr}")
        return False


def list_releases(namespace: Optional[str] = None) -> bool:
    """List Helm releases."""
    print("Listing Helm releases...")
    
    cmd = ["helm", "list"]
    
    if namespace:
        cmd.extend(["--namespace", namespace])
    
    cmd.extend(["-o", "table"])
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(stdout)
        return True
    else:
        print(f"✗ Failed to list releases: {stderr}")
        return False


def get_status(name: str, namespace: Optional[str] = None) -> bool:
    """Get status of a Helm release."""
    print(f"Getting status for: {name}")
    
    cmd = ["helm", "status", name]
    
    if namespace:
        cmd.extend(["--namespace", namespace])
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(stdout)
        return True
    else:
        print(f"✗ Failed to get status: {stderr}")
        return False


def create_namespace(namespace: str) -> bool:
    """Create Kubernetes namespace if not exists."""
    print(f"Ensuring namespace '{namespace}' exists...")
    
    # Check if namespace exists
    success, _, _ = run_command([
        "kubectl", "get", "namespace", namespace
    ])
    
    if success:
        print(f"  Namespace '{namespace}' already exists")
        return True
    
    # Create namespace
    success, stdout, stderr = run_command([
        "kubectl", "create", "namespace", namespace,
        "--dry-run=client", "-o", "yaml"
    ])
    
    if not success:
        print(f"  Warning: Could not prepare namespace: {stderr}")
        return False
    
    # Apply the namespace
    success, stdout, stderr = run_command([
        "kubectl", "apply", "-f", "-"
    ], capture=False)
    
    # Alternative: direct create
    if not success:
        success, stdout, stderr = run_command([
            "kubectl", "create", "namespace", namespace
        ])
    
    if success:
        print(f"✓ Namespace '{namespace}' created")
        return True
    else:
        print(f"  Note: {stderr}")
        return True  # Namespace might already exist


def search_chart(query: str, repo: Optional[str] = None) -> bool:
    """Search for Helm charts."""
    print(f"Searching for chart: {query}")
    
    cmd = ["helm", "search", "repo", query]
    
    if repo:
        cmd = ["helm", "search", "repo", f"{repo}/{query}"]
    
    cmd.extend(["-o", "table"])
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(stdout)
        return True
    else:
        print(f"✗ Failed to search: {stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Helm Operations")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # add-repo
    add_parser = subparsers.add_parser("add-repo", help="Add a Helm repository")
    add_parser.add_argument("name", help="Repository name")
    add_parser.add_argument("url", help="Repository URL")
    
    # update
    subparsers.add_parser("update", help="Update Helm repositories")
    
    # install
    install_parser = subparsers.add_parser("install", help="Install a Helm chart")
    install_parser.add_argument("chart", help="Chart to install (e.g., bitnami/kafka)")
    install_parser.add_argument("name", help="Release name")
    install_parser.add_argument("-n", "--namespace", help="Target namespace")
    install_parser.add_argument("--set", action="append", dest="settings",
                               help="Set values (can be used multiple times)")
    install_parser.add_argument("--no-wait", action="store_true",
                               help="Don't wait for resources to be ready")
    
    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a Helm chart")
    uninstall_parser.add_argument("name", help="Release name")
    uninstall_parser.add_argument("-n", "--namespace", help="Target namespace")
    
    # list
    list_parser = subparsers.add_parser("list", help="List Helm releases")
    list_parser.add_argument("-n", "--namespace", help="Target namespace")
    
    # status
    status_parser = subparsers.add_parser("status", help="Get release status")
    status_parser.add_argument("name", help="Release name")
    status_parser.add_argument("-n", "--namespace", help="Target namespace")
    
    # search
    search_parser = subparsers.add_parser("search", help="Search for charts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--repo", help="Specific repository to search")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "add-repo":
        success = add_repo(args.name, args.url)
    elif args.command == "update":
        success = update_repos()
    elif args.command == "install":
        success = install_chart(
            args.chart,
            args.name,
            args.namespace,
            args.settings,
            not args.no_wait
        )
    elif args.command == "uninstall":
        success = uninstall_chart(args.name, args.namespace)
    elif args.command == "list":
        success = list_releases(args.namespace)
    elif args.command == "status":
        success = get_status(args.name, args.namespace)
    elif args.command == "search":
        success = search_chart(args.query, args.repo)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
