#!/usr/bin/env python3
"""
Example: Google Drive MCP Client

Wrapper for Google Drive MCP server.
Replace with actual MCP server integration.

Usage: python gdrive_client.py <operation> [args...]
"""

import os
import sys
import json
from typing import Any, Dict, Optional

# Import generic MCP client
try:
    from mcp_client import call_mcp_server
except ImportError:
    # Fallback: direct HTTP calls
    import requests
    
    def call_mcp_server(server_url: str, method: str, params: dict = None) -> dict:
        """Call MCP server directly."""
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
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return {"success": False, "error": result["error"].get("message")}
            
            return {"success": True, "data": result.get("result", {})}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Configuration
GDRIVE_MCP_URL = os.getenv(
    "GDRIVE_MCP_URL",
    "http://localhost:8080"  # Google Drive MCP server URL
)


def get_file(file_id: str) -> Dict[str, Any]:
    """
    Get file content from Google Drive.
    
    Args:
        file_id: Google Drive file ID
    
    Returns:
        Minimal result with file content
    """
    result = call_mcp_server(GDRIVE_MCP_URL, "tools/call", {
        "name": "gdrive_get_file",
        "arguments": {"file_id": file_id}
    })
    
    if result["success"]:
        # Return only essential info (token efficient)
        content = result["data"].get("content", [])
        if content:
            text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            return {
                "success": True,
                "file_id": file_id,
                "content_preview": text[:200]  # Only first 200 chars
            }
        return {"success": True, "data": result["data"]}
    else:
        return result


def list_files(folder_id: str = "root", limit: int = 10) -> Dict[str, Any]:
    """
    List files in Google Drive folder.
    
    Args:
        folder_id: Folder ID (default: root)
        limit: Max files to return
    
    Returns:
        Minimal file list
    """
    result = call_mcp_server(GDRIVE_MCP_URL, "tools/call", {
        "name": "gdrive_list_files",
        "arguments": {"folder_id": folder_id, "limit": limit}
    })
    
    if result["success"]:
        # Return only file names and IDs (token efficient)
        files = result["data"].get("files", [])
        return {
            "success": True,
            "count": len(files),
            "files": [{"id": f.get("id"), "name": f.get("name")} for f in files[:limit]]
        }
    else:
        return result


def search_files(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for files in Google Drive.
    
    Args:
        query: Search query
        limit: Max results
    
    Returns:
        Minimal search results
    """
    result = call_mcp_server(GDRIVE_MCP_URL, "tools/call", {
        "name": "gdrive_search",
        "arguments": {"query": query, "limit": limit}
    })
    
    if result["success"]:
        files = result["data"].get("files", [])
        return {
            "success": True,
            "count": len(files),
            "files": [{"id": f.get("id"), "name": f.get("name")} for f in files[:limit]]
        }
    else:
        return result


def create_file(name: str, content: str, folder_id: str = "root") -> Dict[str, Any]:
    """
    Create a new file in Google Drive.
    
    Args:
        name: File name
        content: File content
        folder_id: Parent folder ID
    
    Returns:
        Created file info
    """
    result = call_mcp_server(GDRIVE_MCP_URL, "tools/call", {
        "name": "gdrive_create_file",
        "arguments": {
            "name": name,
            "content": content,
            "folder_id": folder_id
        }
    })
    
    if result["success"]:
        return {
            "success": True,
            "file_id": result["data"].get("file_id"),
            "name": name
        }
    else:
        return result


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print("Usage: python gdrive_client.py <operation> [args...]")
        print("\nOperations:")
        print("  get <file_id>")
        print("  list [folder_id] [limit]")
        print("  search <query> [limit]")
        print("  create <name> <content> [folder_id]")
        sys.exit(1)
    
    operation = sys.argv[1]
    
    if operation == "get":
        if len(sys.argv) < 3:
            print("Error: Missing file_id")
            sys.exit(1)
        
        result = get_file(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif operation == "list":
        folder_id = sys.argv[2] if len(sys.argv) > 2 else "root"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        
        result = list_files(folder_id, limit)
        print(json.dumps(result, indent=2))
    
    elif operation == "search":
        if len(sys.argv) < 3:
            print("Error: Missing query")
            sys.exit(1)
        
        query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        
        result = search_files(query, limit)
        print(json.dumps(result, indent=2))
    
    elif operation == "create":
        if len(sys.argv) < 4:
            print("Error: Missing name or content")
            sys.exit(1)
        
        name = sys.argv[2]
        content = sys.argv[3]
        folder_id = sys.argv[4] if len(sys.argv) > 4 else "root"
        
        result = create_file(name, content, folder_id)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown operation: {operation}")
        sys.exit(1)


if __name__ == "__main__":
    main()
