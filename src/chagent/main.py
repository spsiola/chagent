import sys
import asyncio
from .config import load_config
from .llm_tester import get_working_client
from .agent import AsyncAgent
from .mcp_integration import MCPManager
import uvicorn
from .server import app

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
    
    import os
    env = os.environ.copy()
    env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
    
    print("Starting MCP server...")
    try:
        await mcp_manager.connect_server("npx", ["-y", "@modelcontextprotocol/server-everything"], env=env)
    except Exception as e:
        print(f"Warning: Failed to start test MCP server: {e}")
    
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        app.state.agent = agent
        
        import socket
        port = 4217
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    break
            port += 1
            
        print(f"\n🚀 Веб-сервер запущен! Откройте в браузере: http://127.0.0.1:{port}\n")
        
        server_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        server = uvicorn.Server(server_config)
        
        try:
            await server.serve()
        finally:
            await mcp_manager.close_all()
    else:
        try:
            print("\nЗапуск в режиме CLI. Для веб-сервера используйте флаг 'serve'.")
            await agent.run("What's the weather in Tokyo? Also, use the echo tool to echo 'MCP is fully functional!'.")
        finally:
            await mcp_manager.close_all()

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
