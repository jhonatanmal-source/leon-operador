#!/usr/bin/env python3
"""
MCP Protocol Handler — Base class for MCP servers.
Model Context Protocol over stdio using JSON-RPC 2.0.

Protocol version: 2024-11-05
"""

import json
import sys
import traceback
from typing import Any, Callable


class MCPError(Exception):
    """MCP protocol error with JSON-RPC error code."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ToolDefinition:
    """Definition of an MCP tool."""
    def __init__(self, name: str, description: str, input_schema: dict, handler: Callable):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class MCPBaseHandler:
    """
    Base handler for MCP servers.
    
    Subclasses must implement:
      - register_tools() -> List[ToolDefinition]
    
    The handler reads JSON-RPC requests from stdin and writes responses to stdout.
    """

    def __init__(self, server_name: str, server_version: str = "1.0.0"):
        self.server_name = server_name
        self.server_version = server_version
        self._tools: dict[str, ToolDefinition] = {}
        self._initialized = False
        self.register_tools()

    def register_tools(self):
        """Register all tools. Override in subclass."""
        pass

    def add_tool(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def add_tool_def(self, name: str, description: str, input_schema: dict, handler: Callable):
        self.add_tool(ToolDefinition(name, description, input_schema, handler))

    # --- JSON-RPC handlers ---

    def handle_initialize(self, params: dict | None) -> dict:
        self._initialized = True
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.server_name,
                "version": self.server_version
            }
        }

    def handle_list_tools(self, params: dict | None) -> dict:
        return {
            "tools": [t.to_dict() for t in self._tools.values()]
        }

    def handle_call_tool(self, params: dict | None) -> dict:
        if params is None:
            raise MCPError(INVALID_PARAMS, "Missing params")
        
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            raise MCPError(INVALID_PARAMS, "Missing tool name")
        
        tool = self._tools.get(name)
        if not tool:
            raise MCPError(METHOD_NOT_FOUND, f"Unknown tool: {name}")
        
        # Validate required arguments
        required = tool.input_schema.get("required", [])
        for arg in required:
            if arg not in arguments:
                raise MCPError(INVALID_PARAMS, f"Missing required argument: {arg}")
        
        try:
            result = tool.handler(**arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ]
            }
        except MCPError:
            raise
        except Exception as e:
            raise MCPError(INTERNAL_ERROR, f"Error executing {name}: {str(e)}")

    def handle_notification(self, method: str, params: dict | None):
        """Handle notifications (no response expected)."""
        if method == "notifications/initialized":
            self._initialized = True
        # Silently ignore other notifications

    # --- Request dispatcher ---

    def _dispatch(self, request: dict) -> dict | None:
        method = request.get("method", "")
        params = request.get("params")
        req_id = request.get("id")

        # Notifications have no 'id'
        if req_id is None:
            self.handle_notification(method, params)
            return None

        try:
            match method:
                case "initialize":
                    result = self.handle_initialize(params)
                case "tools/list":
                    result = self.handle_list_tools(params)
                case "tools/call":
                    result = self.handle_call_tool(params)
                case _:
                    raise MCPError(METHOD_NOT_FOUND, f"Method not found: {method}")
            
            return {"jsonrpc": "2.0", "result": result, "id": req_id}
        
        except MCPError as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": e.code, "message": e.message, "data": e.data},
                "id": req_id
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": INTERNAL_ERROR, "message": f"Internal error: {str(e)}"},
                "id": req_id
            }

    # --- Main loop ---

    def run(self):
        """Read JSON-RPC requests from stdin, write responses to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                response = {
                    "jsonrpc": "2.0",
                    "error": {"code": PARSE_ERROR, "message": f"Parse error: {str(e)}"},
                    "id": None
                }
                self._write_response(response)
                continue

            try:
                response = self._dispatch(request)
                if response is not None:
                    self._write_response(response)
            except Exception:
                # Last resort error handling
                self._write_response({
                    "jsonrpc": "2.0",
                    "error": {"code": INTERNAL_ERROR, "message": "Unhandled internal error"},
                    "id": request.get("id")
                })

    def _write_response(self, response: dict):
        line = json.dumps(response, default=str)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def run_server(handler_class, server_name: str = "", server_version: str = ""):
    """Convenience function to run an MCP server.
    
    If server_name is provided, it is passed to the handler constructor
    along with server_version. Otherwise, the handler's own __init__ is used.
    """
    try:
        if server_name:
            handler = handler_class(server_name, server_version)
        else:
            handler = handler_class()
        handler.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
