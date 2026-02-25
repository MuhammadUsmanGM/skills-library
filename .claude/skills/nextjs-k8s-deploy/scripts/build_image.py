#!/usr/bin/env python3
"""
Build Docker Image for Next.js Application

Usage: python build_image.py <app-name>
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, capture: bool = False) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    print(f"  $ {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=600
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def check_docker() -> bool:
    """Check if Docker is available."""
    success, _, stderr = run_command(["docker", "--version"])
    if not success:
        print(f"✗ Docker not found: {stderr}")
        return False
    print("✓ Docker available")
    return True


def check_app_directory(app_name: str) -> bool:
    """Check if app directory and Dockerfile exist."""
    app_dir = Path(app_name)
    
    if not app_dir.exists():
        print(f"✗ Directory not found: {app_dir}")
        return False
    
    if not (app_dir / "Dockerfile").exists():
        print(f"✗ Dockerfile not found in {app_dir}")
        return False
    
    if not (app_dir / "package.json").exists():
        print(f"✗ package.json not found in {app_dir}")
        return False
    
    print(f"✓ App directory validated: {app_dir}")
    return True


def build_image(app_name: str, tag: str = "latest", no_cache: bool = False) -> bool:
    """Build Docker image."""
    image_name = f"{app_name}:{tag}"
    
    print(f"\nBuilding Docker image: {image_name}")
    print("=" * 50)
    
    cmd = ["docker", "build", "-t", image_name]
    
    if no_cache:
        cmd.append("--no-cache")
    
    cmd.append(app_name)
    
    success, stdout, stderr = run_command(cmd, capture=False)
    
    if success:
        print(f"\n✓ Image built: {image_name}")
        return True
    else:
        print(f"\n✗ Build failed")
        return False


def test_image(app_name: str, port: int = 3000) -> bool:
    """Test Docker image locally."""
    print(f"\nTesting image locally on port {port}...")
    
    container_name = f"{app_name}-test"
    
    # Run container
    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "-p", f"{port}:3000",
        f"{app_name}:latest"
    ]
    
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        print(f"✗ Failed to start container: {stderr}")
        return False
    
    print(f"  Container started: {container_name}")
    
    # Wait for startup
    print("  Waiting for application to start...")
    import time
    time.sleep(5)
    
    # Test health endpoint
    import requests
    try:
        response = requests.get(f"http://localhost:{port}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ Health check passed")
        else:
            print(f"  ⚠ Health check returned {response.status_code}")
    except Exception as e:
        print(f"  ⚠ Health check failed: {e}")
    
    # Cleanup
    print(f"  Stopping test container...")
    run_command(["docker", "stop", container_name])
    run_command(["docker", "rm", container_name])
    
    return True


def push_image(app_name: str, registry: str, tag: str = "latest") -> bool:
    """Push image to registry."""
    image_name = f"{app_name}:{tag}"
    registry_image = f"{registry}/{image_name}"
    
    print(f"\nPushing to registry: {registry_image}")
    
    # Tag image
    cmd = ["docker", "tag", image_name, registry_image]
    success, _, stderr = run_command(cmd)
    
    if not success:
        print(f"✗ Failed to tag image: {stderr}")
        return False
    
    # Push
    cmd = ["docker", "push", registry_image]
    success, _, stderr = run_command(cmd, capture=False)
    
    if success:
        print(f"✓ Pushed: {registry_image}")
        return True
    else:
        print(f"✗ Push failed")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build Docker image for Next.js application"
    )
    parser.add_argument("app", help="Application name/directory")
    parser.add_argument("-t", "--tag", default="latest",
                       help="Image tag (default: latest)")
    parser.add_argument("--no-cache", action="store_true",
                       help="Build without cache")
    parser.add_argument("--test", action="store_true",
                       help="Test image after build")
    parser.add_argument("--push", help="Push to registry (e.g., docker.io/user)")
    parser.add_argument("-p", "--port", type=int, default=3000,
                       help="Test port (default: 3000)")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"Building {args.app}")
    print("=" * 50)
    
    # Check prerequisites
    if not check_docker():
        sys.exit(1)
    
    if not check_app_directory(args.app):
        sys.exit(1)
    
    # Build image
    if not build_image(args.app, args.tag, args.no_cache):
        sys.exit(1)
    
    # Test image
    if args.test:
        if not test_image(args.app, args.port):
            print("⚠ Test failed, but build succeeded")
    
    # Push to registry
    if args.push:
        if not push_image(args.app, args.push, args.tag):
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✓ Build complete!")
    print(f"\nImage: {args.app}:{args.tag}")
    print(f"\nNext steps:")
    print(f"  python scripts/deploy.py {args.app} --namespace apps")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
