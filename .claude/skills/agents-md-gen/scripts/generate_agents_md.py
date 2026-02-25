#!/usr/bin/env python3
"""
AGENTS.md Generator - Creates AI agent documentation for repositories.

Usage: python generate_agents_md.py <repo-path>
"""

import os
import sys
from pathlib import Path
from datetime import datetime


def scan_directory(path: str, max_depth: int = 3) -> dict:
    """Scan directory structure up to max_depth levels."""
    result = {"dirs": [], "files": []}
    path = Path(path)
    
    for item in path.rglob("*"):
        # Skip hidden, node_modules, dist, build directories
        if any(part.startswith('.') for part in item.parts):
            continue
        if any(part in ['node_modules', 'dist', 'build', '__pycache__', '.git'] for part in item.parts):
            continue
            
        rel_path = item.relative_to(path)
        depth = len(rel_path.parts)
        
        if depth > max_depth:
            continue
            
        if item.is_file():
            # Skip binary and generated files
            if item.suffix in ['.pyc', '.pyo', '.so', '.dll', '.exe']:
                continue
            result["files"].append(str(rel_path))
        else:
            result["dirs"].append(str(rel_path))
    
    return result


def detect_stack(path: str) -> dict:
    """Detect technology stack from files present."""
    stack = {
        "frontend": [],
        "backend": [],
        "database": [],
        "devops": [],
        "testing": []
    }
    
    path = Path(path)
    
    # Frontend detection
    if (path / "package.json").exists():
        stack["frontend"].append("Node.js")
    if (path / "next.config.js").exists() or (path / "next.config.ts").exists():
        stack["frontend"].append("Next.js")
    if (path / "vite.config.js").exists() or (path / "vite.config.ts").exists():
        stack["frontend"].append("Vite")
    if any(path.glob("*.tsx")):
        stack["frontend"].append("React/TSX")
    if any(path.glob("*.vue")):
        stack["frontend"].append("Vue.js")
    
    # Backend detection
    if any(path.glob("**/requirements.txt")):
        stack["backend"].append("Python")
    if any(path.glob("**/*.py")):
        stack["backend"].append("Python")
    if any(path.glob("**/go.mod")):
        stack["backend"].append("Go")
    if any(path.glob("**/Cargo.toml")):
        stack["backend"].append("Rust")
    if (path / "pom.xml").exists():
        stack["backend"].append("Java/Maven")
    
    # Database detection
    if any(path.glob("**/migrations/**")):
        stack["database"].append("Migrations")
    if any(path.glob("**/*.sql")):
        stack["database"].append("SQL")
    if any(path.glob("**/prisma/**")):
        stack["database"].append("Prisma")
    
    # DevOps detection
    if (path / "Dockerfile").exists() or any(path.glob("**/Dockerfile")):
        stack["devops"].append("Docker")
    if any(path.glob("**/docker-compose*.yml")):
        stack["devops"].append("Docker Compose")
    if any(path.glob("**/*.yaml")) or any(path.glob("**/*.yml")):
        stack["devops"].append("Kubernetes/Helm")
    if (path / ".github" / "workflows").exists():
        stack["devops"].append("GitHub Actions")
    
    # Testing detection
    if any(path.glob("**/*.test.ts")) or any(path.glob("**/*.test.tsx")):
        stack["testing"].append("Jest/Vitest")
    if any(path.glob("**/test_*.py")) or any(path.glob("**/*_test.py")):
        stack["testing"].append("pytest")
    if (path / "jest.config.js").exists():
        stack["testing"].append("Jest")
    
    # Clean empty categories
    return {k: v for k, v in stack.items() if v}


def generate_agents_md(repo_path: str) -> str:
    """Generate AGENTS.md content for repository."""
    path = Path(repo_path)
    structure = scan_directory(repo_path)
    stack = detect_stack(repo_path)
    
    # Build directory tree visualization
    dirs_sorted = sorted(structure["dirs"], key=lambda x: x.count('/'))
    files_sorted = sorted(structure["files"])
    
    tree_lines = []
    seen_dirs = set()
    
    for f in files_sorted[:50]:  # Limit to 50 files
        parts = f.split('/')
        for i in range(len(parts) - 1):
            dir_path = '/'.join(parts[:i+1])
            if dir_path not in seen_dirs:
                seen_dirs.add(dir_path)
                indent = '  ' * i
                tree_lines.append(f"{indent}📁 {parts[i]}/")
        
        indent = '  ' * (len(parts) - 1)
        tree_lines.append(f"{indent}📄 {parts[-1]}")
    
    tree = '\n'.join(tree_lines[:100])  # Limit output
    
    # Generate content
    content = f"""# AGENTS.md - {path.name}

> Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> This file helps AI agents understand the repository structure and conventions.

## Repository Purpose

This repository contains a cloud-native application built with modern microservices architecture.

## Technology Stack

"""
    
    for category, technologies in stack.items():
        if technologies:
            content += f"### {category.title()}\n"
            for tech in technologies:
                content += f"- {tech}\n"
            content += "\n"
    
    content += f"""## Directory Structure

```
{path.name}/
{tree}
```

## Development Conventions

### Code Style
- Follow existing code patterns in each service
- Use TypeScript for frontend, Python for backend services
- Maintain consistent naming: kebab-case for files, camelCase for variables

### Commit Messages
- Format: `<type>: <description>` (e.g., `feat: add user authentication`)
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### File Organization
- Keep related files together
- One component/function per file (when reasonable)
- Co-locate tests with source files

## AI Agent Guidelines

### When Modifying Code
1. Read existing files to understand patterns
2. Follow established conventions
3. Update tests when adding features
4. Keep changes focused and minimal

### When Adding New Features
1. Check for existing similar implementations
2. Use the same patterns and styles
3. Add appropriate error handling
4. Update documentation if needed

### When Debugging
1. Read error messages carefully
2. Check related files for context
3. Look for similar patterns in codebase
4. Test changes before committing

## Key Files

| File | Purpose |
|------|---------|
| `package.json` | Node.js dependencies and scripts |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container build instructions |
| `docker-compose.yml` | Local development environment |

## Commands

### Development
```bash
# Install dependencies
npm install          # Frontend
pip install -r requirements.txt  # Backend

# Run locally
npm run dev          # Frontend development server
python -m uvicorn main:app --reload  # Backend API

# Run tests
npm test
pytest
```

### Build & Deploy
```bash
# Build containers
docker build -t app:latest .

# Deploy to Kubernetes
kubectl apply -f k8s/
```

---

*For more information, see the project documentation in `/docs`*
"""
    
    return content


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_agents_md.py <repo-path>")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    
    if not os.path.isdir(repo_path):
        print(f"Error: '{repo_path}' is not a valid directory")
        sys.exit(1)
    
    content = generate_agents_md(repo_path)
    output_path = os.path.join(repo_path, "AGENTS.md")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ AGENTS.md generated at: {output_path}")
    print(f"  Total lines: {len(content.splitlines())}")


if __name__ == "__main__":
    main()
