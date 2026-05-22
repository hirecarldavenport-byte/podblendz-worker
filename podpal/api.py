import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# -------------------------------------------------
# ✅ SINGLE SOURCE OF TRUTH (CRITICAL FIX)
# -------------------------------------------------

AUDIO_DIR = Path("/app/audio")
TEMP_DIR = AUDIO_DIR / "temp"
FINAL_DIR = AUDIO_DIR / "final"

# ✅ Ensure directories exist BEFORE mount
TEMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

print("✅ AUDIO DIR:", AUDIO_DIR)
print("✅ FINAL DIR:", FINAL_DIR)
print("✅ FINAL EXISTS:", FINAL_DIR.exists())

# -------------------------------------------------
# ✅ App setup
# -------------------------------------------------

app = FastAPI(
    title="PodBlendz API",
    version="0.1.0",
    description="Backend API for search-driven podcast blending",
)

# -------------------------------------------------
# ✅ CORS configuration
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# ✅ STATIC AUDIO SERVING (CORRECTED)
# -------------------------------------------------

app.mount(
    "/audio",
    StaticFiles(directory=str(AUDIO_DIR)),
    name="audio"
)

print("✅ Static assets mounted")

# -------------------------------------------------
# ✅ DEBUG ROUTE (VERY IMPORTANT)
# -------------------------------------------------

@app.get("/debug/audio/{filename}")
def debug_audio(filename: str):
    file_path = FINAL_DIR / filename

    print(f"🔍 Checking file: {file_path}")

    return {
        "exists": file_path.exists(),
        "full_path": str(file_path)
    }

# -------------------------------------------------
# ✅ Import routers
# -------------------------------------------------

from podpal.routes.health import router as health_router
from podpal.routes.search_routes import router as search_router
from podpal.routes.blend_routes import router as blend_router

# -------------------------------------------------
# ✅ Register routers
# -------------------------------------------------

app.include_router(health_router)
app.include_router(search_router)
app.include_router(blend_router)

# -------------------------------------------------
# ✅ Root endpoint
# -------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "status": "ok",
        "service": "PodBlendz API",
        "description": "Blends multiple podcasts into one audio story by topic",
    }
