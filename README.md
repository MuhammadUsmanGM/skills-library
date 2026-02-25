# Skills Library

Reusable AI agent skills for building cloud-native applications with MCP Code Execution.

## Overview

This repository contains skills that teach AI coding agents (Claude Code, Goose, OpenAI Codex) how to build sophisticated cloud-native applications autonomously.

## Skills Architecture

Each skill follows the **MCP Code Execution Pattern**:

```
skill-name/
├── SKILL.md          # Instructions (~100 tokens loaded when triggered)
├── REFERENCE.md      # Deep documentation (loaded on-demand)
└── scripts/
    ├── deploy.sh     # Execution scripts (0 tokens - never loaded)
    ├── verify.py     # Verification scripts
    └── mcp_client.py # MCP wrappers (optional)
```

## Available Skills

| Skill | Purpose |
|-------|---------|
| `agents-md-gen` | Generate AGENTS.md files for repositories |
| `k8s-foundation` | Check cluster health and apply basic Helm charts |
| `kafka-k8s-setup` | Deploy Apache Kafka on Kubernetes |
| `postgres-k8s-setup` | Deploy PostgreSQL with migrations |
| `fastapi-dapr-agent` | Create FastAPI + Dapr microservices |
| `mcp-code-execution` | MCP integration with code execution |
| `nextjs-k8s-deploy` | Deploy Next.js applications |
| `docusaurus-deploy` | Deploy Docusaurus documentation sites |

## Token Efficiency

By using MCP Code Execution instead of direct MCP tool loading:

| Approach | Token Cost |
|----------|------------|
| Direct MCP (5 servers) | ~50,000+ tokens |
| Skills + Code Execution | ~100 tokens |

**Result:** 99% token reduction while maintaining full capability.

## Usage

### With Claude Code

```bash
cd learnflow-app
claude
# Then prompt: "Set up Kafka using the kafka-k8s-setup skill"
```

### With Goose

```bash
cd learnflow-app
goose
# Then prompt: "Deploy PostgreSQL using the postgres-k8s-setup skill"
```

## Creating New Skills

1. Create directory: `.claude/skills/<skill-name>/`
2. Add `SKILL.md` with YAML frontmatter
3. Add `scripts/` directory with execution scripts
4. Optionally add `REFERENCE.md` for deep documentation

See `docs/skill-development-guide.md` for detailed instructions.

## License

MIT
