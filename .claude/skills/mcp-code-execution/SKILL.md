---
name: mcp-code-execution
description: MCP Code Execution pattern for efficient AI agent operations
---

# MCP Code Execution Pattern

## When to Use
- Integrating MCP servers without token bloat
- Processing large datasets before returning to agent
- Wrapping external APIs with minimal context usage
- Building efficient AI agent workflows

## Instructions

### Create MCP Wrapper
1. Run generator: `python scripts/create_mcp_wrapper.py <server-name>`
2. Configure endpoints in generated client
3. Test: `python scripts/test_mcp_client.py <server-name>`

### Execute MCP Operations
1. Use wrapper: `python scripts/<server>_client.py <operation> [args]`
2. Results returned with minimal tokens
3. Only essential data enters agent context

## Token Efficiency

| Approach | Tokens Used |
|----------|-------------|
| Direct MCP (5 servers) | ~50,000+ |
| MCP Code Execution | ~100 |

**Savings:** 99%+ token reduction

## Pattern Architecture

```
SKILL.md (100 tokens)
    ↓
scripts/mcp_client.py (0 tokens - executed)
    ↓
MCP Server API (external)
    ↓
Minimal result (10 tokens)
```

## Validation
- [ ] Wrapper script executes without errors
- [ ] Returns minimal, formatted output
- [ ] No large data in agent context
- [ ] Error handling works correctly

See [REFERENCE.md](./REFERENCE.md) for MCP server examples and best practices.
