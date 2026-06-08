from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, robots, commands, poses
from app.core.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database on startup
    await init_db()
    yield

app = FastAPI(title="Grabber Robot Service", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(robots.router, prefix="/api/robots", tags=["robots"])
# Commands and poses use the robotId path parameter inside the prefix
app.include_router(commands.router, prefix="/api/robots/{robotId}/commands", tags=["commands"])
app.include_router(poses.router, prefix="/api/robots/{robotId}/poses", tags=["poses"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Grabber Robot Service"}
