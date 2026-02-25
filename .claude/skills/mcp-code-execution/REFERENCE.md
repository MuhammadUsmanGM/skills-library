# MCP Code Execution Reference

## Pattern Overview

The MCP Code Execution pattern minimizes token usage by executing MCP calls in external scripts rather than loading MCP tool definitions directly into the agent's context.

### Before: Direct MCP (Token Heavy)

```
Agent Context:
├── MCP Tool Definitions (50,000+ tokens)
├── Tool Schemas
├── API Documentation
└── Your Conversation
```

### After: Code Execution (Token Efficient)

```
Agent Context:
├── SKILL.md (~100 tokens)
└── Your Conversation

External Execution:
└── scripts/mcp_client.py (0 tokens in context)
    └── Returns minimal result (~10 tokens)
```

## Implementation Guide

### Step 1: Create Skill Structure

```
.claude/skills/mcp-integration/
├── SKILL.md
├── REFERENCE.md
└── scripts/
    ├── mcp_client.py      # Generic MCP client
    ├── server_client.py   # Specific server wrapper
    └── test_client.py     # Test script
```

### Step 2: Write SKILL.md

```markdown
---
name: mcp-integration
description: MCP integration via code execution
---

# MCP Integration

## Instructions
1. Run: `python scripts/server_client.py <operation> [args]`
2. Review minimal output
3. Proceed with task

See REFERENCE.md for configuration.
```

### Step 3: Create MCP Client

```python
#!/usr/bin/env python3
"""MCP Client - executes externally, 0 tokens loaded"""

import requests
import os

def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call MCP server and return minimal result."""
    
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    response = requests.post(f"{server_url}/mcp", json=payload)
    result = response.json()
    
    # Return only essential data (token efficient)
    if "result" in result:
        content = result["result"].get("content", [])
        if content:
            return {
                "success": True,
                "data": content[0].get("text", "")[:500]  # Truncate
            }
    
    return {"success": False, "error": "Unknown error"}
```

### Step 4: Use in Agent Workflow

```
User: "Get my Google Drive files"

Agent loads SKILL.md (100 tokens)
    ↓
Agent executes: python scripts/gdrive_client.py list
    ↓
Script calls MCP server externally (0 tokens)
    ↓
Returns: {"success": true, "count": 5, "files": [...]}
    ↓
Agent displays result (50 tokens)

Total: ~150 tokens vs 50,000+ with direct MCP
```

## Example MCP Wrappers

### Google Drive

```python
# gdrive_client.py
def get_file(file_id: str) -> dict:
    result = call_mcp_tool("gdrive_get_file", {"file_id": file_id})
    
    if result["success"]:
        # Return only preview (token efficient)
        return {
            "file_id": file_id,
            "preview": result["data"][:200]
        }
    return result
```

### Salesforce

```python
# salesforce_client.py
def get_record(record_id: str) -> dict:
    result = call_mcp_tool("sf_get_record", {"id": record_id})
    
    if result["success"]:
        # Return only key fields
        data = result["data"]
        return {
            "id": record_id,
            "name": data.get("Name"),
            "type": data.get("Type")
        }
    return result
```

### Database

```python
# database_client.py
def query(sql: str) -> dict:
    result = call_mcp_tool("db_query", {"sql": sql})
    
    if result["success"]:
        rows = result["data"].get("rows", [])
        # Return only first 10 rows (token efficient)
        return {
            "count": len(rows),
            "rows": rows[:10],
            "columns": result["data"].get("columns")
        }
    return result
```

## Token Comparison

| Operation | Direct MCP | Code Execution | Savings |
|-----------|------------|----------------|---------|
| List files | ~10,000 | ~150 | 98.5% |
| Get document | ~25,000 | ~200 | 99.2% |
| Search + Update | ~50,000 | ~300 | 99.4% |

## Best Practices

### DO
- Keep SKILL.md minimal (~100 tokens)
- Execute all MCP calls in scripts
- Return only essential data
- Truncate long outputs
- Handle errors gracefully

### DON'T
- Load MCP tool definitions in context
- Return full documents/records
- Print verbose debug info
- Return raw API responses

## Environment Configuration

```bash
# Set MCP server URL
export MCP_SERVER_URL="http://localhost:8080"

# Set authentication
export MCP_API_KEY="your-api-key"

# Set timeout
export MCP_TIMEOUT="60"
```

## Testing

```bash
# Test connection
python scripts/mcp_client.py health http://localhost:8080

# List available tools
python scripts/mcp_client.py list http://localhost:8080

# Call a tool
python scripts/mcp_client.py call http://localhost:8080 tool_name --args key=value
```

## Error Handling

```python
def safe_mcp_call(tool_name: str, arguments: dict) -> dict:
    """MCP call with comprehensive error handling."""
    
    try:
        result = call_mcp_tool(tool_name, arguments)
        
        if result.get("success"):
            return {"status": "ok", "data": result["data"]}
        else:
            return {"status": "error", "message": result.get("error")}
    
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out"}
    
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Cannot connect to MCP server"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Advanced: Batch Operations

```python
def batch_process(items: list, operation: str) -> dict:
    """Process multiple items efficiently."""
    
    results = []
    errors = []
    
    for item in items:
        result = call_mcp_tool(operation, {"item": item})
        
        if result["success"]:
            results.append(item)
        else:
            errors.append({"item": item, "error": result["error"]})
    
    # Return summary (token efficient)
    return {
        "total": len(items),
        "success": len(results),
        "failed": len(errors),
        "errors": errors[:5]  # Only first 5 errors
    }
```

## Security Considerations

### API Key Management

```python
import os

# Never hardcode API keys
API_KEY = os.getenv("MCP_API_KEY")  # ✓ Good

# Use environment variables or secret managers
if not API_KEY:
    raise ValueError("MCP_API_KEY not set")
```

### Input Validation

```python
def safe_query(user_input: str) -> dict:
    """Validate input before MCP call."""
    
    # Sanitize input
    if not user_input.isalnum():
        return {"status": "error", "message": "Invalid input"}
    
    if len(user_input) > 1000:
        return {"status": "error", "message": "Input too long"}
    
    return call_mcp_tool("search", {"query": user_input})
```

## Troubleshooting

### Connection Refused

```bash
# Check if MCP server is running
curl http://localhost:8080/health

# Check firewall
netstat -an | grep 8080
```

### Timeout Errors

```bash
# Increase timeout
export MCP_TIMEOUT="120"

# Check server performance
top -p $(pgrep -f mcp-server)
```

### Authentication Failures

```bash
# Verify API key
echo $MCP_API_KEY

# Test with curl
curl -H "Authorization: Bearer $MCP_API_KEY" http://localhost:8080/health
```

## Related Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [Anthropic MCP Code Execution](https://www.anthropic.com/engineering/code-execution-with-mcp)
