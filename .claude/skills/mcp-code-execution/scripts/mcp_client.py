#!/usr/bin/env python3
"""
Generic MCP Client - Call any MCP server with minimal tokens

Usage: 
    python mcp_client.py call <server-url> <tool-name> --args key=value
    python mcp_client.py list <server-url>
    python mcp_client.py health <server-url>
"""

import argparse
import sys
import json
import requests
from typing import Any, Dict, List, Optional


def call_mcp_server(
    server_url: str,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Call MCP server with JSON-RPC.
    
    Args:
        server_url: MCP server URL
        method: JSON-RPC method
        params: Method parameters
        timeout: Request timeout
    
    Returns:
        Minimal result dictionary
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    try:
        response = requests.post(
            f"{server_url}/mcp",
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Return minimal result
        if "error" in result:
            return {
                "success": False,
                "error": result["error"].get("message", "Unknown error")
            }
        
        return {"success": True, "data": result.get("result", {})}
        
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}


def list_tools(server_url: str) -> bool:
    """List available tools on MCP server."""
    print(f"Listing tools on {server_url}...")
    
    result = call_mcp_server(server_url, "tools/list")
    
    if result["success"]:
        tools = result["data"].get("tools", [])
        
        if not tools:
            print("  No tools found")
            return True
        
        print(f"\nAvailable tools ({len(tools)}):")
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "No description")[:80]
            print(f"  • {name}: {description}")
        
        return True
    else:
        print(f"  ✗ Error: {result['error']}")
        return False


def call_tool(
    server_url: str,
    tool_name: str,
    arguments: Dict[str, Any]
) -> bool:
    """Call a tool on MCP server."""
    print(f"Calling {tool_name} on {server_url}...")
    print(f"  Arguments: {json.dumps(arguments)}")
    
    result = call_mcp_server(server_url, "tools/call", {
        "name": tool_name,
        "arguments": arguments
    })
    
    if result["success"]:
        # Print minimal result (token efficient)
        data = result["data"]
        content = data.get("content", [])
        
        if content:
            # Extract text content
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    # Truncate long output
                    if len(text) > 500:
                        text = text[:500] + "... (truncated)"
                    print(f"\nResult:\n{text}")
                else:
                    print(f"\nResult:\n{json.dumps(item, indent=2)}")
        else:
            print(f"\nResult:\n{json.dumps(data, indent=2)}")
        
        return True
    else:
        print(f"  ✗ Error: {result['error']}")
        return False


def check_health(server_url: str) -> bool:
    """Check MCP server health."""
    print(f"Checking health of {server_url}...")
    
    # Try basic HTTP health check
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("  ✓ Server is healthy")
            return True
    except:
        pass
    
    # Try MCP health method
    result = call_mcp_server(server_url, "health")
    
    if result["success"]:
        print("  ✓ MCP server is healthy")
        return True
    else:
        print(f"  ✗ Server error: {result['error']}")
        return False


def parse_args(args: List[str]) -> Dict[str, Any]:
    """Parse key=value arguments."""
    result = {}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            # Try to parse as JSON
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generic MCP Client - Call any MCP server"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # list
    list_parser = subparsers.add_parser("list", help="List available tools")
    list_parser.add_argument("server", help="MCP server URL")
    
    # call
    call_parser = subparsers.add_parser("call", help="Call a tool")
    call_parser.add_argument("server", help="MCP server URL")
    call_parser.add_argument("tool", help="Tool name")
    call_parser.add_argument("--args", nargs="*", default=[],
                            help="Arguments as key=value")
    call_parser.add_argument("--json", help="Arguments as JSON string")
    
    # health
    health_parser = subparsers.add_parser("health", help="Check server health")
    health_parser.add_argument("server", help="MCP server URL")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "list":
        success = list_tools(args.server)
    
    elif args.command == "call":
        # Parse arguments
        if args.json:
            arguments = json.loads(args.json)
        else:
            arguments = parse_args(args.args)
        
        success = call_tool(args.server, args.tool, arguments)
    
    elif args.command == "health":
        success = check_health(args.server)
    
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
