"""
podpal/api.py

Primary FastAPI entrypoint for PodBlendz.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------
# Directories
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_DIR = BASE_DIR / "media"
TEMP_DIR = MEDIA_DIR / "temp"
FINAL_DIR = MEDIA_DIR / "final"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

print(f"✅ MEDIA_DIR: {MEDIA_DIR}")
print(f"✅ TEMP_DIR: {TEMP_DIR}")
print(f"✅ FINAL_DIR: {FINAL_DIR}")

# ---------------------------------------------------------
# FastAPI
# ---------------------------------------------------------

app = FastAPI(
    title="PodBlendz API",
    version="1.0.0",
    description="AI-powered podcast blending platform",
)

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Static Audio
# ---------------------------------------------------------

app.mount(
    "/audio",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="audio",
)

print("✅ Audio mount active")

# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

from podpal.routes.health import router as health_router
from podpal.routes.search_routes import router as search_router

# Optional routes
try:
    from podpal.routes.blend_routes import router as blend_router
except Exception as e:
    blend_router = None
    print("⚠️ blend_router unavailable:", e)

try:
    from podpal.routes.blend_feed_routes import (
        router as blend_feed_router
    )
except Exception as e:
    blend_feed_router = None
    print("⚠️ blend_feed_router unavailable:", e)

try:
    from podpal.routes.catalog_routes import (
        router as catalog_router
    )
except Exception as e:
    catalog_router = None
    print("⚠️ catalog_router unavailable:", e)

# ---------------------------------------------------------
# Register Routers
# ---------------------------------------------------------

app.include_router(health_router)

app.include_router(search_router)

if blend_router:
    app.include_router(blend_router)

if blend_feed_router:
    app.include_router(blend_feed_router)

if catalog_router:
    app.include_router(catalog_router)

# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "status": "ok",
        "service": "PodBlendz API",
        "version": "1.0.0",
        "description": "Generates Shared Perspectives podcast blends"
    }


# ---------------------------------------------------------
# Debug Audio
# ---------------------------------------------------------

@app.get("/debug/audio")
def debug_audio():

    files = []

    if FINAL_DIR.exists():
        files = [f.name for f in FINAL_DIR.glob("*")]

    return {
        "count": len(files),
        "files": files
    }


@app.get("/debug/audio/{filename}")
def debug_audio_file(filename: str):

    file_path = FINAL_DIR / filename

    return {
        "exists": file_path.exists(),
        "path": str(file_path),
        "size": (
            file_path.stat().st_size
            if file_path.exists()
            else 0
        ),
    }
