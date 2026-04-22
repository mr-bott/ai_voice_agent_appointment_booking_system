"""
Main entry point for the Voice AI Clinical Agent Backend.
This file initializes the FastAPI application, sets up middleware, 
handles database migrations on startup, and includes API routers.
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent.tools import ensure_demo_data
from .api import rest, websocket
from .database.connection import AsyncSessionLocal, Base, engine
from .api.metrics import metrics_store
from .database.models import Appointment, AvailabilitySlot, CampaignJob, Doctor, MemoryLog, Patient


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            await ensure_demo_data(session)
    except Exception as exc:
        print(f"Startup warning: backend dependencies not fully ready: {exc}")

    yield


app = FastAPI(
    title="Voice AI Clinical Agent API",
    description="Real-Time Multilingual Voice AI Agent for Clinical Appointment Booking",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    return metrics_store.get_metrics()


app.include_router(websocket.router)
app.include_router(rest.router, prefix="/api", tags=["REST APIs"])


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
