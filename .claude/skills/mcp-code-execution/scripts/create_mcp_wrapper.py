#!/usr/bin/env python3
"""
Create MCP Wrapper Script - Generates MCP client wrappers

Usage: python create_mcp_wrapper.py <server-name>
"""

import argparse
import sys
from pathlib import Path


def create_mcp_client(server_name: str) -> str:
    """Create MCP client wrapper."""
    return f'''#!/usr/bin/env python3
"""
{server_name.title()} MCP Client

Wrapper for {server_name} MCP server with code execution pattern.
Executes externally - 0 tokens loaded into agent context.
"""

import os
import sys
import json
import requests
from typing import Any, Dict, Optional


# Configuration
MCP_SERVER_URL = os.getenv(
    "{server_name.upper()}_MCP_URL",
    "http://localhost:8080"  # Default MCP server URL
)
TIMEOUT = int(os.getenv("MCP_TIMEOUT", "30"))


def call_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    server_url: str = None
) -> Dict[str, Any]:
    """
    Call MCP server tool and return minimal result.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments
        server_url: MCP server URL (optional)
    
    Returns:
        Minimal result dictionary
    """
    url = server_url or MCP_SERVER_URL
    
    payload = {{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {{
            "name": tool_name,
            "arguments": arguments
        }}
    }}
    
    try:
        response = requests.post(
            f"{{url}}/mcp",
            json=payload,
            timeout=TIMEOUT,
            headers={{"Content-Type": "application/json"}}
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract only essential data
        if "result" in result:
            content = result["result"].get("content", [])
            if content:
                return {{
                    "success": True,
                    "data": content[0].get("text", "") if len(content) == 1 else content
                }}
        
        return {{"success": True, "data": result}}
        
    except requests.exceptions.RequestException as e:
        return {{"success": False, "error": str(e)}}
    except json.JSONDecodeError as e:
        return {{"success": False, "error": f"Invalid JSON response: {{e}}"}}


# ============== Tool Functions ==============

def example_tool(param1: str, param2: Optional[str] = None) -> Dict[str, Any]:
    """
    Example tool function - replace with actual MCP tools.
    
    Args:
        param1: First parameter
        param2: Optional second parameter
    
    Returns:
        Minimal result
    """
    result = call_mcp_tool("example_tool", {{
        "param1": param1,
        "param2": param2
    }})
    
    if result["success"]:
        # Return only essential info (token efficient)
        return {{"status": "success", "result": result["data"][:100]}}
    else:
        return {{"status": "error", "message": result["error"]}}


# ============== Main ==============

def main():
    """CLI interface for MCP client."""
    if len(sys.argv) < 2:
        print("Usage: python {server_name}_client.py <tool> [args...]")
        print("\nAvailable tools:")
        print("  example_tool <param1> [param2]")
        sys.exit(1)
    
    tool = sys.argv[1]
    
    if tool == "example_tool":
        if len(sys.argv) < 3:
            print("Error: Missing param1")
            sys.exit(1)
        
        param1 = sys.argv[2]
        param2 = sys.argv[3] if len(sys.argv) > 3 else None
        
        result = example_tool(param1, param2)
        
        # Output minimal result (token efficient)
        print(json.dumps(result, indent=2))
        
    else:
        print(f"Unknown tool: {{tool}}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''


def create_mcp_wrapper_template(server_name: str) -> str:
    """Create reusable MCP wrapper template."""
    return f'''#!/usr/bin/env python3
"""
{server_name.title()} MCP Wrapper Template

Reusable wrapper for {server_name} MCP server.
Import and use in your own scripts.
"""

from typing import Any, Dict, Optional
import requests
import os


class {server_name.replace("-", "_").title().replace("_", "")}MCPClient:
    """MCP client for {server_name} server."""
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        self.server_url = server_url or os.getenv(
            "{server_name.upper()}_MCP_URL",
            "http://localhost:8080"
        )
        self.timeout = timeout
        self.api_key = api_key or os.getenv("{server_name.upper()}_API_KEY")
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {{self.api_key}}"
    
    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call MCP tool and return result."""
        payload = {{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {{
                "name": tool_name,
                "arguments": arguments
            }}
        }}
        
        try:
            response = self.session.post(
                f"{{self.server_url}}/mcp",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                return {{
                    "success": False,
                    "error": result["error"].get("message", "Unknown error")
                }}
            
            return {{
                "success": True,
                "data": result.get("result", {{}})
            }}
            
        except requests.exceptions.RequestException as e:
            return {{"success": False, "error": str(e)}}
    
    # Add your specific tool methods here
    # Example:
    # def get_data(self, id: str) -> Dict[str, Any]:
    #     return self.call_tool("get_data", {{"id": id}})


# Usage example
if __name__ == "__main__":
    client = {server_name.replace("-", "_").title().replace("_", "")}MCPClient()
    # result = client.get_data("example")
    # print(result)
'''


def create_test_script(server_name: str) -> str:
    """Create test script for MCP client."""
    return f'''#!/usr/bin/env python3
"""
Test {server_name.title()} MCP Client

Usage: python test_mcp_client.py
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the client
try:
    from {server_name}_client import call_mcp_tool, example_tool
except ImportError as e:
    print(f"Error importing client: {{e}}")
    print("Make sure {server_name}_client.py exists in the scripts directory")
    sys.exit(1)


def test_connection() -> bool:
    """Test MCP server connection."""
    print("Testing MCP server connection...")
    
    result = call_mcp_tool("health", {{}})
    
    if result.get("success"):
        print("✓ Connection successful")
        return True
    else:
        print(f"✗ Connection failed: {{result.get('error', 'Unknown error')}}")
        return False


def test_example_tool() -> bool:
    """Test example tool."""
    print("\\nTesting example tool...")
    
    result = example_tool("test_param")
    
    if result.get("status") == "success":
        print(f"✓ Tool executed successfully")
        print(f"  Result: {{result.get('result', 'N/A')}}")
        return True
    else:
        print(f"✗ Tool failed: {{result.get('message', 'Unknown error')}}")
        return False


def main():
    print("=" * 50)
    print(f"{server_name.title()} MCP Client Test")
    print("=" * 50)
    
    tests = [
        ("Connection", test_connection),
        ("Example Tool", test_example_tool),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {{name}} test error: {{e}}")
            failed += 1
    
    print("\\n" + "=" * 50)
    print(f"Results: {{passed}} passed, {{failed}} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("⚠ Some tests failed")
        print("\\nNote: MCP server may not be running")
        print(f"Set {{server_name.upper()}}_MCP_URL environment variable if needed")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''


def create_readme(server_name: str) -> str:
    """Create README for MCP client."""
    return f'''# {server_name.title()} MCP Client

MCP client wrapper for {server_name} server with code execution pattern.

## Quick Start

### Set Environment Variables

```bash
export {server_name.upper()}_MCP_URL="http://localhost:8080"
export {server_name.upper()}_API_KEY="your-api-key"  # If required
```

### Run Client

```bash
# Test connection
python test_mcp_client.py

# Use CLI
python {server_name}_client.py example_tool <param1> [param2]
```

### Use as Library

```python
from {server_name}_client import call_mcp_tool

result = call_mcp_tool("tool_name", {{
    "param1": "value1",
    "param2": "value2"
}})

if result["success"]:
    print(result["data"])
else:
    print(f"Error: {{result['error']}}")
```

## Token Efficiency

This client follows the MCP Code Execution pattern:

1. **SKILL.md** loads (~100 tokens)
2. **Client script** executes (0 tokens loaded)
3. **Minimal result** returned (~10 tokens)

**Total:** ~110 tokens vs 50,000+ with direct MCP

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `example_tool` | Example tool | param1, param2 (optional) |
| `health` | Health check | none |

## Adding New Tools

1. Add tool function in `{server_name}_client.py`:

```python
def my_tool(param: str) -> Dict[str, Any]:
    result = call_mcp_tool("my_tool", {{"param": param}})
    
    if result["success"]:
        return {{"status": "success", "data": result["data"]}}
    else:
        return {{"status": "error", "message": result["error"]}}
```

2. Add CLI handler in `main()`:

```python
elif tool == "my_tool":
    result = my_tool(sys.argv[2])
    print(json.dumps(result, indent=2))
```

## Troubleshooting

### Connection Refused

```bash
# Check if MCP server is running
curl http://localhost:8080/health

# Set correct URL
export {server_name.upper()}_MCP_URL="http://your-server:8080"
```

### Authentication Error

```bash
# Set API key
export {server_name.upper()}_API_KEY="your-api-key"
```

### Timeout

```bash
# Increase timeout
export MCP_TIMEOUT="60"
```
'''


def create_mcp_wrapper(server_name: str) -> bool:
    """Generate complete MCP wrapper structure."""
    scripts_dir = Path(f"skills-library/.claude/skills/{server_name}/scripts")
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    files = {
        scripts_dir / f"{server_name}_client.py": create_mcp_client(server_name),
        scripts_dir / f"{server_name}_wrapper.py": create_mcp_wrapper_template(server_name),
        scripts_dir / "test_mcp_client.py": create_test_script(server_name),
        scripts_dir / "README.md": create_readme(server_name),
    }
    
    for path, content in files.items():
        with open(path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created {path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create MCP wrapper for a server"
    )
    parser.add_argument("server", help="Server name (e.g., google-drive, salesforce)")
    
    args = parser.parse_args()
    
    print(f"Creating MCP wrapper for {args.server}...")
    print("=" * 50)
    
    if create_mcp_wrapper(args.server):
        print("\n" + "=" * 50)
        print(f"✓ MCP wrapper created for {args.server}")
        print(f"\nNext steps:")
        print(f"  1. Configure {args.server.upper()}_MCP_URL")
        print(f"  2. Run: python test_mcp_client.py")
        print(f"  3. Customize tools in {args.server}_client.py")
        sys.exit(0)
    else:
        print("\n✗ Failed to create wrapper")
        sys.exit(1)


if __name__ == "__main__":
    main()
