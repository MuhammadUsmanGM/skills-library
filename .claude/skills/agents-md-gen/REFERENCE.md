# AGENTS.md Reference

## What is AGENTS.md?

AGENTS.md is a markdown file placed in the root of a repository to help AI coding agents (Claude Code, Goose, Copilot, etc.) understand:

1. **Repository purpose** - What this project does
2. **Directory structure** - How code is organized
3. **Technology stack** - What frameworks and tools are used
4. **Development conventions** - Coding standards and patterns
5. **AI guidelines** - How agents should interact with the codebase

## Why AGENTS.md Matters

Without AGENTS.md, AI agents must:
- Infer structure from scanning files
- Make assumptions about conventions
- Potentially violate project patterns

With AGENTS.md, AI agents can:
- Understand intent immediately
- Follow established patterns
- Make consistent changes

## Best Practices

### DO
- Keep it concise (under 500 lines)
- Include actual directory tree
- Document key commands
- Specify commit message format
- Update when structure changes significantly

### DON'T
- Duplicate README.md content
- Include sensitive information
- Over-document obvious conventions
- Let it become stale

## Template Structure

```markdown
# AGENTS.md - <project-name>

## Repository Purpose
<1-2 sentence description>

## Technology Stack
- Frontend: ...
- Backend: ...
- Database: ...

## Directory Structure
<tree visualization>

## Development Conventions
- Code style
- Commit messages
- File organization

## AI Agent Guidelines
- How to modify code
- How to add features
- How to debug

## Key Files
| File | Purpose |

## Commands
<development and deployment commands>
```

## Examples

### Example 1: Next.js + FastAPI Project

```markdown
# AGENTS.md - LearnFlow

## Repository Purpose
AI-powered Python tutoring platform with Next.js frontend and FastAPI microservices.

## Technology Stack
- Frontend: Next.js 14, React, TypeScript, TailwindCSS
- Backend: FastAPI, Python 3.11, Dapr
- Database: PostgreSQL (Neon)
- Messaging: Kafka
- Orchestration: Kubernetes

## Directory Structure
learnflow-app/
├── apps/
│   ├── frontend/        # Next.js application
│   ├── triage-service/  # Request routing service
│   └── concepts-service/# Concept explanation service
├── packages/
│   ├── shared/          # Shared types and utilities
│   └── mcp-servers/     # MCP server implementations
└── docs/                # Docusaurus documentation
```

### Example 2: Monorepo with Multiple Services

```markdown
# AGENTS.md - Microservices Platform

## Repository Purpose
Event-driven microservices platform for real-time data processing.

## Technology Stack
- Services: Go, Python, Node.js
- Messaging: Kafka, Redis Streams
- Infrastructure: Kubernetes, Helm, Dapr
- CI/CD: GitHub Actions, Argo CD
```

## Generation Tips

When generating AGENTS.md:

1. **Scan the repository** - Identify key directories and files
2. **Detect the stack** - Look for package.json, requirements.txt, etc.
3. **Identify patterns** - Note naming conventions, file organization
4. **Document commands** - Find common dev/test/deploy commands
5. **Keep it current** - Note when it was generated

## Validation Checklist

- [ ] Repository purpose is clear
- [ ] Directory structure is accurate
- [ ] Technology stack is correct
- [ ] Key commands are documented
- [ ] AI guidelines are helpful
- [ ] File is under 500 lines

## Related Resources

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Goose Documentation](https://block.github.io/goose/)
- [Model Context Protocol](https://modelcontextprotocol.io)
