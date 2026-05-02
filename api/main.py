"""FastAPI main application for AI Takeoff Builder GUI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import config, projects, pipeline, system, files, export

app = FastAPI(
    title="AI Takeoff Builder API",
    description="Backend API for the AI Takeoff Builder GUI",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://localhost:80",
        "https://assign.jobotai.site",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router)
app.include_router(projects.router)
app.include_router(files.router)  # /files/* endpoints
app.include_router(pipeline.router)
app.include_router(system.router)
app.include_router(export.router)


@app.get("/")
def root() -> dict:
    return {"message": "AI Takeoff Builder API", "version": "1.0.0"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
