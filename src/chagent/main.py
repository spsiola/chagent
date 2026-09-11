import sys
import os
import asyncio
from .config import load_config
from .llm_tester import get_working_client
from .agent import AsyncAgent
from .mcp_integration import MCPManager
from .skill_loader import load_skills
from .mcp_loader import load_mcp_configs
from .memory_manager import MemoryManager
from .settings import load_settings
from .native_tools import register_native_tools
import uvicorn
from .server import app

async def get_weather(location: str) -> str:
    """Mock standard skill."""
    return f"The weather in {location} is sunny and 25°C."

async def _default_logger(msg: str) -> None:
    print(msg)

async def initialize_system(log_callback=_default_logger):
    try:
        await log_callback("Harness: Loading config...")
        config = load_config()
        app.state.startup_timeout = getattr(config, "startup_timeout", 30)
        
        await log_callback("Harness: Testing models to find a working provider...")
        client, model, provider_name = await get_working_client(config, log_callback)
        
        if not client or not model:
            await log_callback("Harness: Fatal: Could not initialize any LLM.")
            return
            
        # Создаем базовые директории, если их нет
        for d in ["data", "data/skills", "data/memory"]:
            os.makedirs(d, exist_ok=True)
            
        # Seeding: если рабочие файлы/директории пусты, копируем из init_memory
        import shutil
        init_mcp = "init_memory/mcp_config.json"
        data_mcp = "data/mcp_config.json"
        if not os.path.exists(data_mcp) and os.path.exists(init_mcp):
            shutil.copy2(init_mcp, data_mcp)
            
        init_help = "init_memory/HOW_IT_WORKS.md"
        data_help = "data/HOW_IT_WORKS.md"
        if not os.path.exists(data_help) and os.path.exists(init_help):
            shutil.copy2(init_help, data_help)
            
        init_skills_dir = "init_memory/skills"
        data_skills_dir = "data/skills"
        if os.path.exists(init_skills_dir) and not os.listdir(data_skills_dir):
            for item in os.listdir(init_skills_dir):
                s = os.path.join(init_skills_dir, item)
                d = os.path.join(data_skills_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            
        app.state.settings = load_settings()
        app.state.memory_manager = MemoryManager()
        
        prompt = app.state.memory_manager.get_prompt_for_model(f"{provider_name}/{model}")
        
        prompt_builder = lambda base_prompt, tools: app.state.memory_manager.build_system_prompt(f"{app.state.agent.provider_name}/{app.state.agent.model}" if hasattr(app.state, 'agent') and app.state.agent else f"{provider_name}/{model}", tools)
        
        agent = AsyncAgent(
            client, 
            model, 
            system_prompt=prompt,
            provider_name=provider_name,
            prompt_builder_func=prompt_builder,
            session_id=getattr(app.state, 'session_id', "default"),
            stats_manager=getattr(app.state, 'stats_manager', None)
        )
        
        # Регистрируем нативные инструменты для работы с ФС и ОС
        register_native_tools(agent, app.state.settings)
        
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
            
        # Загружаем скилы из SKILL.md
        await load_skills(agent, log_callback=log_callback)
        
        # Загружаем MCP серверы
        await load_mcp_configs(app.state.mcp_manager, log_callback=log_callback)
        
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
