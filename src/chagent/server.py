import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from openai import AsyncOpenAI
from .config import load_config
from .llm_tester import test_model
from .settings import AppSettings, save_settings

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    if hasattr(app.state, 'initialize_system_func'):
        asyncio.create_task(app.state.initialize_system_func(app.state.manager.broadcast_harness_log))
    yield
    if getattr(app.state, 'mcp_manager', None):
        await app.state.mcp_manager.close_all()

# Initialize FastAPI app
app = FastAPI(title="chagent", description="AI Agent with MCP support", lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
    
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.harness_logs: list[str] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send past harness logs to newly connected clients
        for log in self.harness_logs:
            await websocket.send_json({"type": "harness_log", "content": log})

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_harness_log(self, message: str):
        self.harness_logs.append(message)
        for connection in self.active_connections:
            try:
                await connection.send_json({"type": "harness_log", "content": message})
            except Exception:
                pass

manager = ConnectionManager()
app.state.manager = manager
app.state.agent_ready = asyncio.Event()
app.state.agent = None

@app.get("/")
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Static files not found. Please create index.html in static directory.</h1>")

@app.get("/api/help")
async def get_help():
    """Возвращает содержимое справки из data/HOW_IT_WORKS.md"""
    try:
        with open("data/HOW_IT_WORKS.md", "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except Exception:
        return {"content": "Справка не найдена."}

@app.get("/api/tools")
async def get_tools():
    """Возвращает актуальный список инструментов агента (agent.tools)"""
    if getattr(app.state, 'agent', None):
        return {"tools": app.state.agent.tools}
    return {"tools": []}

class SwitchModelRequest(BaseModel):
    provider_name: str
    model_name: str

@app.get("/api/models")
async def get_models():
    config = load_config()
    models_list = []
    current_provider = None
    for provider in config.providers:
        for model in provider.models:
            models_list.append({"provider": provider.name, "model": model})
            
    current_agent = app.state.agent
    current_active_model = None
    if current_agent:
        current_active_model = current_agent.model
        # Optional: try to find current provider by matching base_url/api_key
        # but just returning current_model is enough for UI.

    return {"models": models_list, "current_model": current_active_model}

@app.post("/api/models/switch")
async def switch_model(request: SwitchModelRequest):
    config = load_config()
    target_provider = None
    for p in config.providers:
        if p.name == request.provider_name:
            target_provider = p
            break
            
    if not target_provider:
        return {"success": False, "error": "Provider not found"}
        
    if request.model_name not in target_provider.models:
        return {"success": False, "error": "Model not found in provider"}
        
    app.state.agent_ready.clear()
    await app.state.manager.broadcast_harness_log(f"Harness: Switching to model {request.model_name} (Provider: {request.provider_name})...")
    
    # Initialize client
    api_key = target_provider.api_key
    if api_key.startswith("ENV_"):
        env_var = api_key[4:]
        api_key = os.environ.get(env_var, "placeholder")
        
    client = AsyncOpenAI(
        base_url=target_provider.base_url,
        api_key=api_key,
    )
    
    # Test model
    success = await test_model(client, request.model_name, app.state.manager.broadcast_harness_log)
    if success:
        if app.state.agent:
            app.state.agent.client = client
            app.state.agent.model = request.model_name
            app.state.agent.provider_name = request.provider_name
            
            # Обновляем системный промпт для новой модели
            if hasattr(app.state, 'memory_manager'):
                new_prompt = app.state.memory_manager.get_prompt_for_model(f"{request.provider_name}/{request.model_name}")
                app.state.agent.base_system_prompt = new_prompt
                
            await app.state.manager.broadcast_harness_log(f"Harness: ✅ Successfully switched to model '{request.model_name}'")
        else:
            await app.state.manager.broadcast_harness_log("Harness: Agent not initialized yet, cannot switch.")
            success = False
    else:
        await app.state.manager.broadcast_harness_log(f"Harness: ❌ Failed to switch. Chat disabled until a working model is selected.")
        
    app.state.agent_ready.set()
    return {"success": success}

# --- Settings & Memory API ---

@app.get("/api/settings")
async def get_settings():
    if hasattr(app.state, 'settings'):
        return app.state.settings.model_dump()
    return {}

@app.post("/api/settings")
async def update_settings(settings: AppSettings):
    app.state.settings = settings
    save_settings(settings)
    return {"success": True}

@app.get("/api/memory/prompts")
async def get_prompts():
    if hasattr(app.state, 'memory_manager'):
        return app.state.memory_manager.get_all_prompts()
    return {}

class UpdatePromptRequest(BaseModel):
    model_id: Optional[str] = None # "default" or "provider/model"
    prompt: Optional[str] = None
    tool_rules: Optional[str] = None
    system_template: Optional[str] = None

@app.post("/api/memory/prompts")
async def update_prompt(req: UpdatePromptRequest):
    if hasattr(app.state, 'memory_manager'):
        if req.tool_rules is not None:
            app.state.memory_manager.update_tool_rules(req.tool_rules)
            
        if req.system_template is not None:
            app.state.memory_manager.update_system_template(req.system_template)
            
        if req.model_id and req.prompt is not None:
            if req.model_id == "default":
                app.state.memory_manager.update_default_prompt(req.prompt)
            else:
                app.state.memory_manager.update_model_prompt(req.model_id, req.prompt)
                
            # Если промпт обновлен для текущей модели (или дефолтный), сразу обновляем агента
            agent = app.state.agent
            if agent:
                current_id = f"{agent.provider_name}/{agent.model}"
                if req.model_id == current_id or (req.model_id == "default" and current_id not in app.state.memory_manager.prompts.models):
                    agent.base_system_prompt = req.prompt
                    
        return {"success": True}
    return {"success": False, "error": "Memory manager not initialized"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive text from client
            data = await websocket.receive_text()
            
            try:
                msg_data = json.loads(data)
                prompt = msg_data.get("text", "")
            except json.JSONDecodeError:
                prompt = data
                
            if not prompt:
                continue
            
            # Message queuing logic
            if not app.state.agent_ready.is_set():
                timeout = getattr(app.state, "startup_timeout", 30)
                try:
                    await asyncio.wait_for(app.state.agent_ready.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    await manager.broadcast_harness_log(f"Harness: Сообщение не обработано и сброшено. ЛЛМ не загрузилась за {timeout} сек.")
                    continue
            
            agent = app.state.agent
            if not agent:
                await manager.broadcast_harness_log("Harness: Сообщение сброшено, инициализация провалилась.")
                continue

            # Stream events back to the client
            try:
                async for event in agent.stream_run(prompt):
                    await websocket.send_json(event)
            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
