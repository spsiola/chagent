import json
import os
import asyncio

async def _default_logger(msg: str) -> None:
    print(msg)

async def load_mcp_configs(mcp_manager, config_paths=["data/mcp_config.json"], log_callback=_default_logger):
    """
    Асинхронно загружает конфигурации MCP серверов из списка путей и подключает их.
    Ожидаемый формат JSON: {"mcpServers": {"server-name": {"command": "...", "args": [], "env": {}}}}
    """
    loaded_count = 0
    for path in config_paths:
        if not os.path.exists(path):
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            servers = data.get("mcpServers", {})
            for name, config in servers.items():
                command = config.get("command")
                if not command:
                    print(f"Пропуск {name} в {path}: нет команды")
                    continue
                    
                args = config.get("args", [])
                env = config.get("env", None)
                
                # env needs to be merged with current env if provided, or just passed
                # The stdio_client uses current env automatically if env is None, 
                # but if we specify env, we should probably merge it with os.environ.
                merged_env = None
                if env:
                    merged_env = os.environ.copy()
                    merged_env.update(env)
                    
                msg = f"⏳ Подключение к MCP серверу '{name}' из {path}..."
                if asyncio.iscoroutinefunction(log_callback): await log_callback(msg)
                else: log_callback(msg)
                
                try:
                    await mcp_manager.connect_server(command=command, args=args, env=merged_env)
                    loaded_count += 1
                except Exception as e:
                    msg = f"❌ Ошибка подключения к MCP '{name}': {e}"
                    if asyncio.iscoroutinefunction(log_callback): await log_callback(msg)
                    else: log_callback(msg)
                    
        except json.JSONDecodeError as e:
            msg = f"Ошибка парсинга JSON {path}: {e}"
            if asyncio.iscoroutinefunction(log_callback): await log_callback(msg)
            else: log_callback(msg)
        except Exception as e:
            msg = f"Ошибка чтения {path}: {e}"
            if asyncio.iscoroutinefunction(log_callback): await log_callback(msg)
            else: log_callback(msg)
            
    return loaded_count
