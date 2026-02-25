---
name: agents-md-gen
description: Generate AGENTS.md files for repositories
---

# AGENTS.md Generator

## When to Use
- Creating a new repository
- Adding AI agent documentation to existing project
- Updating repository structure documentation

## Instructions
1. Run generator: `python scripts/generate_agents_md.py <repo-path>`
2. Review generated file
3. Commit to repository root

## Output
Creates AGENTS.md with:
- Repository purpose
- Directory structure
- Development conventions
- AI agent guidelines

## Validation
- [ ] AGENTS.md created in repository root
- [ ] Structure accurately reflects codebase
- [ ] Conventions documented clearly

See [REFERENCE.md](./REFERENCE.md) for AGENTS.md best practices.
