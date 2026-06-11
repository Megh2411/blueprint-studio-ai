from dotenv import load_dotenv
load_dotenv()  # Must be at the top!

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import json

# --- IMPORTS ---
# This is the crucial line that was missing! It imports your render endpoints.
from app.api.routes import renders 
from app.utils.optimizer import optimize_prompt
from app.utils.rate_limiter import RateLimiter

app = FastAPI()

# Allow all origins for frictionless production deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. THE MISSING LINK: Attach the Renders Router ---
# This tells FastAPI to route all /api/renders traffic to your renders.py file
app.include_router(renders.router, prefix="/api/renders", tags=["Renders"])

# --- 2. The Agentic LLM Optimizer ---
class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/prompt/optimize", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def optimize_prompt_endpoint(request: PromptRequest):
    optimized = await optimize_prompt(request.prompt)
    return {"optimized_prompt": optimized}

# --- 3. The WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message))

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# --- 4. The Celery Webhook ---
@app.post("/api/notify-render-complete")
async def notify_render_complete(payload: dict):
    client_id = payload.get("user_id")
    status = payload.get("status", "completed")
    await manager.send_personal_message({
        "status": status,
        "render_path": payload.get("render_path"),
        "metrics": payload.get("metrics")
    }, client_id)
    return {"status": "dispatched"}