#!/usr/bin/env python3
"""
Create Ingress for Docusaurus Site

Usage: python create_ingress.py <site-name> --domain docs.example.com
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_command(cmd: list, input_data: Optional[str] = None) -> tuple:
    """Run command and return (success, stdout, stderr)."""
    print(f"  $ {' '.join(cmd)}")
    try:
        if input_data:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=input_data)
            return proc.returncode == 0, stdout, stderr
        else:
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


def create_ingress(
    site_name: str,
    namespace: str,
    domain: str,
    ingress_class: str = "nginx"
) -> bool:
    """Create Kubernetes ingress for Docusaurus site."""
    print(f"\nCreating ingress for {site_name}...")
    
    ingress_yaml = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {site_name}-ingress
  namespace: {namespace}
  annotations:
    kubernetes.io/ingress.class: {ingress_class}
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - {domain}
    secretName: {site_name}-tls
  rules:
  - host: {domain}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {site_name}
            port:
              number: 80
"""
    
    # Apply ingress
    success, stdout, stderr = run_command(
        ["kubectl", "apply", "-f", "-"],
        input_data=ingress_yaml
    )
    
    if success:
        print(f"✓ Ingress created for {domain}")
        return True
    else:
        print(f"✗ Failed to create ingress: {stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create Kubernetes ingress for Docusaurus site"
    )
    parser.add_argument("site_name", help="Name of the Docusaurus site")
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain for the site (e.g., docs.example.com)"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="docs",
        help="Namespace (default: docs)"
    )
    parser.add_argument(
        "--ingress-class",
        default="nginx",
        help="Ingress class (default: nginx)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Docusaurus Ingress Configuration")
    print("=" * 60)
    
    success = create_ingress(
        args.site_name,
        args.namespace,
        args.domain,
        args.ingress_class
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✓ Ingress configuration complete!")
        print(f"\nNext steps:")
        print(f"  1. Ensure cert-manager is installed for TLS")
        print(f"  2. Configure DNS to point to your ingress controller")
        print(f"  3. Access site at https://{args.domain}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
