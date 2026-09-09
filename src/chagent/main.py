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

async def initialize_system(log_callback=print):
    try:
        await log_callback("Harness: Loading config...")
        config = load_config()
        app.state.startup_timeout = getattr(config, "startup_timeout", 30)
        
        await log_callback("Harness: Testing models to find a working provider...")
        client, model, provider_name = await get_working_client(config, log_callback)
        
        if not client or not model:
            await log_callback("Harness: Fatal: Could not initialize any LLM.")
            return
            
        agent = AsyncAgent(
            client, 
            model, 
            system_prompt="Вы полезный ИИ-ассистент. У вас есть инструменты (tools). Если пользователь задает вопрос (например, о погоде), для которого есть инструмент, вы ОБЯЗАНЫ вызвать инструмент, а не отказываться отвечать. Отвечайте всегда на русском языке.",
            provider_name=provider_name
        )
        
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
        
        app.state.mcp_manager = MCPManager(agent)
        
        # (We removed the default test MCP server-everything here because it confuses small models like 7b with generic tools like echo)
        
        # Set agent and trigger event
        app.state.agent = agent
        app.state.agent_ready.set()
        await log_callback("Harness: Инициализация завершена. Агент готов к работе.")
        
    except Exception as e:
        await log_callback(f"Harness: Ошибка инициализации: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # Wire up background initialization
        app.state.initialize_system_func = initialize_system
            
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
            server.run()
        except KeyboardInterrupt:
            pass
    else:
        # CLI Mode
        async def cli_mode():
            async def sync_print(msg):
                print(msg)
            await initialize_system(sync_print)
            if app.state.agent:
                print("\nЗапуск в режиме CLI. Для веб-сервера используйте флаг 'serve'.")
                try:
                    await app.state.agent.run("What's the weather in Tokyo?")
                finally:
                    if hasattr(app.state, 'mcp_manager') and app.state.mcp_manager:
                        await app.state.mcp_manager.close_all()
        
        try:
            asyncio.run(cli_mode())
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
