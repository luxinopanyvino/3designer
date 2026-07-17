from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import export, health, sessions

app = FastAPI(title="PrintCAD", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(export.router, prefix="/api")
