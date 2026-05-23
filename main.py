"""
AI Colour Matching App — FastAPI Backend
Main entry point
"""
import sys
import os

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import get_settings
from models import create_tables

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Colour Matching & Dye Recipe API for the Garment Industry",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for mobile app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for local dev
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Import and register routes
from routes.auth_routes import router as auth_router
from routes.session_routes import router as session_router
from routes.colour_routes import router as colour_router
from routes.license_routes import router as license_router

app.include_router(auth_router)
app.include_router(session_router)
app.include_router(colour_router)
app.include_router(license_router)


@app.on_event("startup")
def startup():
    """Create database tables on startup."""
    create_tables()
    print(f"\n{'='*50}")
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  Database: {settings.DATABASE_URL}")
    print(f"  Docs: http://localhost:8000/docs")
    print(f"{'='*50}\n")


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
