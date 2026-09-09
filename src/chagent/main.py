import sys
import asyncio
from .config import load_config
from .llm_tester import get_working_client
from .agent import AsyncAgent
from .mcp_integration import MCPManager

async def get_weather(location: str) -> str:
    """Mock standard skill."""
    return f"The weather in {location} is sunny and 25°C."

async def async_main():
    print("Loading config...")
    config = load_config()
    
    print("Testing models to find a working provider...")
    client, model = await get_working_client(config)
    
    if not client or not model:
        print("Fatal: Could not initialize any LLM.")
        sys.exit(1)
        
    agent = AsyncAgent(client, model)
    
    # Register a standard skill
    agent.register_tool(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
        },
        func=get_weather
    )
    
    # Init MCP manager
    mcp_manager = MCPManager(agent)
    
    # Connect a sample MCP server
    import os
    env = os.environ.copy()
    # Ensure standard paths are available for npx
    env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
    
    print("Starting MCP server...")
    try:
        await mcp_manager.connect_server("npx", ["-y", "@modelcontextprotocol/server-everything"], env=env)
    except Exception as e:
        print(f"Warning: Failed to start test MCP server: {e}")
    
    try:
        await agent.run("What's the weather in Tokyo? Also, use the echo tool to echo 'MCP is fully functional!'.")
    finally:
        await mcp_manager.close_all()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
