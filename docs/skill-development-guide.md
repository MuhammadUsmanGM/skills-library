# Skill Development Guide

A comprehensive guide for creating reusable AI agent skills with MCP Code Execution.

## Overview

Skills are the emerging standard for teaching AI coding agents (Claude Code, Goose, OpenAI Codex) how to build sophisticated applications autonomously. This guide covers the **MCP Code Execution Pattern** which provides 99%+ token efficiency compared to direct MCP integration.

## Architecture

### The Token Problem

When you connect MCP servers directly to an agent:

| MCP Servers | Token Cost BEFORE Conversation |
|-------------|-------------------------------|
| 1 server (5 tools) | ~10,000 tokens |
| 3 servers (15 tools) | ~30,000 tokens |
| 5 servers (25 tools) | ~50,000+ tokens |

### The Solution: Skills + Code Execution

```
SKILL.md (~100 tokens)
    ↓
scripts/*.py (0 tokens - executed, not loaded)
    ↓
MCP Server / External API
    ↓
Minimal result (~10 tokens)

Total: ~110 tokens vs 50,000+ with direct MCP
```

## Skill Structure

```
skill-name/
├── SKILL.md              # Instructions (~100 tokens)
├── REFERENCE.md          # Deep documentation (loaded on-demand)
└── scripts/
    ├── deploy.sh         # Execution scripts
    ├── verify.py         # Verification scripts
    └── mcp_client.py     # MCP wrappers (optional)
```

## Creating Your First Skill

### Step 1: Define the Skill Purpose

What task should the AI agent learn? Examples:
- Deploy Kafka to Kubernetes
- Generate AGENTS.md files
- Create FastAPI microservices
- Deploy Next.js applications

### Step 2: Write SKILL.md

```markdown
---
name: skill-name
description: One-line description of what the skill does
---

# Skill Title

## When to Use
- User asks to do X
- Setting up Y component
- Need Z functionality

## Instructions
1. Run: `python scripts/action.py [args]`
2. Verify: `python scripts/verify.py [args]`
3. Confirm success criteria

## Validation
- [ ] Criteria 1
- [ ] Criteria 2

See [REFERENCE.md](./REFERENCE.md) for details.
```

### Step 3: Create Execution Scripts

```python
#!/usr/bin/env python3
"""
Script that performs the actual work.
Executes externally - 0 tokens loaded into agent context.
"""

import subprocess
import sys
import json

def main():
    # Do the work
    result = perform_task()
    
    # Return minimal output (token efficient)
    print(json.dumps({
        "success": True,
        "message": "Task completed",
        "details": result[:100]  # Truncate for token efficiency
    }, indent=2))

if __name__ == "__main__":
    main()
```

### Step 4: Test the Skill

```bash
# Test script directly
python scripts/action.py

# Test with Claude Code
claude
# Then: "Use the skill-name skill to do X"
```

## Best Practices

### DO

1. **Keep SKILL.md minimal** (~100 tokens)
   - Only essential instructions
   - Clear step-by-step guidance
   - Validation checklist

2. **Execute scripts externally**
   - Scripts never loaded into context
   - Only results enter context
   - Truncate long outputs

3. **Handle errors gracefully**
   - Return structured error messages
   - Provide actionable feedback
   - Exit with proper codes

4. **Use REFERENCE.md for depth**
   - Configuration options
   - Troubleshooting guides
   - Advanced examples

### DON'T

1. **Don't load large data into context**
   - No full file contents
   - No API responses > 1KB
   - Use summaries instead

2. **Don't skip error handling**
   - Always check return codes
   - Validate inputs
   - Handle edge cases

3. **Don't hardcode values**
   - Use environment variables
   - Accept command-line arguments
   - Make scripts reusable

## Skill Patterns

### Pattern 1: Deployment Skill

```
skill-name/
├── SKILL.md
├── REFERENCE.md
└── scripts/
    ├── deploy.py    # Deploy resources
    ├── verify.py    # Verify deployment
    └── rollback.py  # Rollback if needed
```

**Example:** `kafka-k8s-setup`

### Pattern 2: Generator Skill

```
skill-name/
├── SKILL.md
├── REFERENCE.md
└── scripts/
    ├── generate.py   # Generate code/files
    ├── validate.py   # Validate output
    └── templates/    # Template files
```

**Example:** `agents-md-gen`

### Pattern 3: MCP Wrapper Skill

```
skill-name/
├── SKILL.md
├── REFERENCE.md
└── scripts/
    ├── mcp_client.py  # Generic MCP client
    ├── server_client.py  # Specific server wrapper
    └── test_client.py  # Test script
```

**Example:** `mcp-code-execution`

## Token Optimization Techniques

### 1. Truncate Output

```python
# Bad: Returns full content
return {"content": full_document}

# Good: Returns preview
return {"preview": full_document[:200] + "..."}
```

### 2. Summarize Results

```python
# Bad: Returns all items
return {"items": all_1000_items}

# Good: Returns summary
return {
    "total": len(all_items),
    "first_10": all_items[:10]
}
```

### 3. Use Status Codes

```python
# Return minimal status
print("✓ Done")  # 10 tokens
# Instead of:
print("The operation completed successfully with no errors...")  # 50+ tokens
```

## Testing Skills

### Manual Testing

```bash
# Test each script
python scripts/deploy.py --help
python scripts/verify.py

# Test with Claude Code
claude
> "Use the kafka-k8s-setup skill to deploy Kafka"
```

### Automated Testing

```python
# tests/test_skill.py
def test_deploy_script():
    result = subprocess.run(
        ["python", "scripts/deploy.py", "--dry-run"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "success" in result.stdout
```

## Publishing Skills

### Repository Structure

```
skills-library/
├── README.md
├── .claude/skills/
│   ├── agents-md-gen/
│   ├── kafka-k8s-setup/
│   └── ...
└── docs/
    └── skill-development-guide.md
```

### Usage Instructions

Add to your repository README:

```markdown
## Using Skills

### With Claude Code

```bash
cd your-project
claude
# Then: "Use the <skill-name> skill to..."
```

### With Goose

```bash
cd your-project
goose
# Skills in .claude/skills/ are automatically available
```
```

## Advanced Topics

### Chaining Skills

Skills can call other skills for complex workflows:

```python
# In a workflow script
subprocess.run(["python", "scripts/kafka-deploy.py"])
subprocess.run(["python", "scripts/kafka-verify.py"])
subprocess.run(["python", "scripts/create-topics.py"])
```

### Dynamic Skill Generation

Generate skills programmatically:

```python
def create_skill(name: str, instructions: str, scripts: list):
    skill_dir = Path(f".claude/skills/{name}")
    skill_dir.mkdir(parents=True)
    
    # Create SKILL.md
    (skill_dir / "SKILL.md").write_text(instructions)
    
    # Copy scripts
    for script in scripts:
        shutil.copy(script, skill_dir / "scripts/")
```

### Skill Versioning

```markdown
---
name: skill-name
version: 1.0.0
description: Skill description
changelog:
  - 1.0.0: Initial release
  - 1.1.0: Added verification step
---
```

## Troubleshooting

### Skill Not Recognized

1. Check SKILL.md is in correct location: `.claude/skills/<name>/SKILL.md`
2. Verify YAML frontmatter syntax
3. Check for required fields: `name`, `description`

### Scripts Not Executing

1. Make scripts executable: `chmod +x scripts/*.py`
2. Check Python shebang: `#!/usr/bin/env python3`
3. Verify dependencies installed

### Token Usage Still High

1. Check script output length
2. Truncate long responses
3. Use summaries instead of full data
4. Move detailed docs to REFERENCE.md

## Resources

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Goose Skills Guide](https://block.github.io/goose/docs/guides/context-engineering/using-skills)
- [MCP Code Execution Pattern](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [OpenAI Codex Skills](https://github.com/openai/codex/blob/main/docs/skills.md)

## Contributing

To contribute skills to this library:

1. Fork the repository
2. Create skill following this guide
3. Test with Claude Code and Goose
4. Submit pull request with:
   - SKILL.md
   - All scripts
   - REFERENCE.md (optional)
   - Tests (recommended)

---

*Remember: The skill is the product. Write skills that work autonomously.*
