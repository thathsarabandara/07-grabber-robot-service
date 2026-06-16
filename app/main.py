import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, robots, commands, poses
from app.core.db import init_db
from app.core.config import settings
from app.services.mqtt_subscriber import mqtt_subscriber_task, heartbeat_monitor_task
from app.services.websocket_manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database on startup
    await init_db()
    
    # Start background tasks
    app.state.mqtt_task = asyncio.create_task(mqtt_subscriber_task())
    app.state.heartbeat_task = asyncio.create_task(heartbeat_monitor_task())
    
    yield
    
    # Cancel background tasks on shutdown
    app.state.mqtt_task.cancel()
    app.state.heartbeat_task.cancel()
    try:
        await app.state.mqtt_task
        await app.state.heartbeat_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Grabber Robot Service", lifespan=lifespan, PORT=settings.PORT)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/api/v1/robots/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(robots.router, prefix="/api/v1/robots", tags=["robots"])
app.include_router(commands.router, prefix="/api/v1/robots/{robotId}/commands", tags=["commands"])
app.include_router(poses.router, prefix="/api/v1/robots/{robotId}/poses", tags=["poses"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Grabber Robot Service"}
