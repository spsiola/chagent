import asyncio
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .agent import AsyncAgent

class MCPManager:
    def __init__(self, agent: AsyncAgent):
        self.agent = agent
        self.contexts = [] # Keep references to prevent GC

    async def connect_server(self, command: str, args: list[str], env: dict[str, str] = None):
        """Connect to an MCP server and register its tools on the agent."""
        print(f"🔌 Connecting to MCP server: {command} {' '.join(args)}")
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        # Open context managers
        cm_client = stdio_client(server_params)
        read, write = await cm_client.__aenter__()
        
        cm_session = ClientSession(read, write)
        session = await cm_session.__aenter__()
        
        self.contexts.append((cm_client, cm_session))
        
        await session.initialize()
        
        # List tools and register them
        response = await session.list_tools()
        for tool in response.tools:
            # We need to map the JSON schema to OpenAI format
            # MCP schema usually matches JSON Schema closely.
            input_schema = getattr(tool, "input_schema", {}) or {}
            
            # Create a wrapper function that calls the MCP tool
            async def execute_mcp_tool(tool_name=tool.name, **kwargs) -> Any:
                print(f"    [MCP] Calling {tool_name} with {kwargs}")
                res = await session.call_tool(tool_name, arguments=kwargs)
                if getattr(res, "isError", False):
                    return f"Error: {res}"
                # Format the result content
                return "\\n".join([c.text for c in res.content if hasattr(c, "text")])
            
            self.agent.register_tool(
                name=tool.name,
                description=tool.description or f"MCP tool {tool.name}",
                parameters=input_schema,
                func=execute_mcp_tool
            )
            print(f"  ✅ Registered MCP tool: {tool.name}")
            
    async def close_all(self):
        for cm_client, cm_session in reversed(self.contexts):
            try:
                await cm_session.__aexit__(None, None, None)
                await cm_client.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing MCP connection: {e}")
