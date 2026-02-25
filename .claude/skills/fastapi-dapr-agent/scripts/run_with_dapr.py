#!/usr/bin/env python3
"""
Run FastAPI service with Dapr sidecar

Usage: python run_with_dapr.py <service-name> --port 8080
"""

import argparse
import subprocess
import sys
import os
import signal
import time
from pathlib import Path


def check_dapr_installed() -> bool:
    """Check if Dapr CLI is installed."""
    try:
        result = subprocess.run(
            ["dapr", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_dapr_initialized() -> bool:
    """Check if Dapr is initialized."""
    try:
        result = subprocess.run(
            ["dapr", "init", "--check"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def run_with_dapr(service_name: str, port: int, app_dir: Path) -> bool:
    """Run service with Dapr sidecar."""
    print(f"Starting {service_name} with Dapr...")
    print(f"  App port: {port}")
    print(f"  Dapr HTTP port: 3500")
    print(f"  Dapr gRPC port: 50001")
    print("=" * 50)
    
    # Change to app directory
    os.chdir(app_dir)
    
    # Build dapr run command
    cmd = [
        "dapr", "run",
        "--app-id", service_name,
        "--app-port", str(port),
        "--dapr-http-port", "3500",
        "--dapr-grpc-port", "50001",
        "--config", f"{service_name}-config",
        "--",
        "python", "main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("\nPress Ctrl+C to stop\n")
    
    # Handle signals
    def signal_handler(sig, frame):
        print("\nShutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    return True


def run_simple(service_name: str, port: int, app_dir: Path) -> bool:
    """Run service without Dapr (simple mode)."""
    print(f"Starting {service_name} (without Dapr)...")
    print(f"  Port: {port}")
    print("=" * 50)
    
    os.chdir(app_dir)
    
    cmd = [
        "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run FastAPI service with Dapr"
    )
    parser.add_argument("service", help="Service name/directory")
    parser.add_argument("-p", "--port", type=int, default=8080,
                       help="Service port (default: 8080)")
    parser.add_argument("--no-dapr", action="store_true",
                       help="Run without Dapr sidecar")
    
    args = parser.parse_args()
    
    app_dir = Path(args.service)
    
    if not app_dir.exists():
        print(f"✗ Service directory not found: {app_dir}")
        sys.exit(1)
    
    if not (app_dir / "main.py").exists():
        print(f"✗ main.py not found in {app_dir}")
        sys.exit(1)
    
    if not args.no_dapr:
        if not check_dapr_installed():
            print("✗ Dapr CLI not found")
            print("\nInstall Dapr:")
            print("  macOS: brew install dapr/tap/dapr-cli")
            print("  Windows: winget install dapr-cli")
            print("  Linux: https://docs.dapr.io/getting-started/install-dapr-cli/")
            print("\nOr run with --no-dapr flag")
            sys.exit(1)
        
        success = run_with_dapr(args.service, args.port, app_dir)
    else:
        success = run_simple(args.service, args.port, app_dir)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
