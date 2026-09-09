import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI(title="chagent", description="AI Agent with MCP support")

# We will mount static files, but if index.html is there we can also serve it directly on GET /
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
    
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Static files not found. Please create index.html in static directory.</h1>")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # We retrieve the agent from the app state (set up in main.py)
    agent = app.state.agent
    
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
                
            # Stream events back to the client
            try:
                async for event in agent.stream_run(prompt):
                    await websocket.send_json(event)
            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})
                
    except WebSocketDisconnect:
        print("Client disconnected")
