#!/usr/bin/env python3
"""
Build Docusaurus Site

Usage: python build.py <site-name>
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
            cwd=Path.cwd(),
            timeout=300
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", f"Command not found: {cmd[0]}"


def check_node() -> bool:
    """Check if Node.js is available."""
    success, stdout, stderr = run_command(["node", "--version"])
    if not success:
        print(f"✗ Node.js not found: {stderr}")
        return False
    print(f"✓ Node.js available: {stdout.strip()}")
    return True


def check_npm() -> bool:
    """Check if npm is available."""
    success, stdout, stderr = run_command(["npm", "--version"])
    if not success:
        print(f"✗ npm not found: {stderr}")
        return False
    print(f"✓ npm available: {stdout.strip()}")
    return True


def install_dependencies(site_dir: Path) -> bool:
    """Install npm dependencies."""
    print(f"\nInstalling dependencies...")
    
    success, stdout, stderr = run_command(["npm", "ci"], capture=False)
    
    if success:
        print("✓ Dependencies installed")
        return True
    else:
        print(f"✗ Failed to install dependencies")
        return False


def build_site(site_dir: Path) -> bool:
    """Build Docusaurus site."""
    print(f"\nBuilding site...")
    
    success, stdout, stderr = run_command(["npm", "run", "build"], capture=False)
    
    if success:
        print("✓ Site built successfully")
        print(f"  Output: {site_dir / 'build'}")
        return True
    else:
        print(f"✗ Build failed")
        return False


def build_docker_image(site_name: str, site_dir: Path) -> bool:
    """Build Docker image."""
    print(f"\nBuilding Docker image...")
    
    # Check if Dockerfile exists
    if not (site_dir / "Dockerfile").exists():
        print("  ✗ Dockerfile not found")
        return False
    
    success, _, stderr = run_command([
        "docker", "build",
        "-t", f"{site_name}:latest",
        str(site_dir)
    ], capture=False)
    
    if success:
        print(f"✓ Docker image built: {site_name}:latest")
        return True
    else:
        print(f"✗ Docker build failed: {stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build Docusaurus documentation site"
    )
    parser.add_argument("site", help="Site name/directory")
    parser.add_argument("--skip-deps", action="store_true",
                       help="Skip dependency installation")
    parser.add_argument("--docker", action="store_true",
                       help="Build Docker image after build")
    
    args = parser.parse_args()
    
    site_dir = Path(args.site)
    
    if not site_dir.exists():
        print(f"✗ Directory not found: {site_dir}")
        sys.exit(1)
    
    if not (site_dir / "package.json").exists():
        print(f"✗ Not a Docusaurus site: {site_dir}")
        sys.exit(1)
    
    print("=" * 50)
    print(f"Building {args.site}")
    print("=" * 50)
    
    # Change to site directory
    import os
    os.chdir(site_dir)
    
    # Check prerequisites
    if not check_node():
        sys.exit(1)
    
    if not check_npm():
        sys.exit(1)
    
    # Install dependencies
    if not args.skip_deps:
        if not install_dependencies(site_dir):
            sys.exit(1)
    
    # Build site
    if not build_site(site_dir):
        sys.exit(1)
    
    # Build Docker image
    if args.docker:
        if not build_docker_image(args.site, site_dir):
            print("⚠ Docker build failed, but site build succeeded")
    
    print("\n" + "=" * 50)
    print("✓ Build complete!")
    print(f"\nNext steps:")
    print(f"  python scripts/deploy.py {args.site} --namespace docs")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
