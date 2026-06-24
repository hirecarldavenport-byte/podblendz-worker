from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from podpal.routes.blend_feed_routes import (
     router as blend_feed_router
)


# -------------------------------------------------
# ✅ SINGLE SOURCE OF TRUTH
# -------------------------------------------------

AUDIO_DIR = Path("/app/audio")
TEMP_DIR = AUDIO_DIR / "temp"
FINAL_DIR = AUDIO_DIR / "final"

# ✅ Ensure directories exist BEFORE mounting
TEMP_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

print("✅ AUDIO DIR:", AUDIO_DIR)
print("✅ TEMP DIR:", TEMP_DIR)
print("✅ FINAL DIR:", FINAL_DIR)

# ✅ DEBUG: show files present at startup
print("📂 Initial FINAL contents:", list(FINAL_DIR.glob("*")))

# -------------------------------------------------
# ✅ FASTAPI APP
# -------------------------------------------------

app = FastAPI(
    title="PodBlendz API",
    version="0.1.0",
    description="Backend API for podcast blending",
)

# -------------------------------------------------
# ✅ CORS
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# ✅ STATIC FILE SERVING (CRITICAL FIX)
# -------------------------------------------------

# ✅ IMPORTANT: mount AFTER directory exists
app.mount(
    "/audio",
    StaticFiles(directory=str(AUDIO_DIR), html=False),
    name="audio"
)

print("✅ Static /audio mounted to:", AUDIO_DIR)

# -------------------------------------------------
# ✅ DEBUG ENDPOINTS
# -------------------------------------------------

@app.get("/debug/audio")
def list_audio():
    files = [f.name for f in FINAL_DIR.glob("*")]
    print("📂 FINAL FILES:", files)
    return {"files": files}


@app.get("/debug/audio/{filename}")
def check_audio(filename: str):
    file_path = FINAL_DIR / filename

    exists = file_path.exists()

    print(f"🔍 Checking: {file_path} → exists={exists}")

    return {
        "exists": exists,
        "path": str(file_path),
        "size": file_path.stat().st_size if exists else 0
    }

# -------------------------------------------------
# ✅ IMPORT ROUTERS
# -------------------------------------------------

from podpal.routes.health import router as health_router
from podpal.routes.search_routes import router as search_router
from podpal.routes.blend_routes import router as blend_router

# -------------------------------------------------
# ✅ REGISTER ROUTERS
# -------------------------------------------------

app.include_router(health_router)
app.include_router(search_router)
app.include_router(blend_router)
app.include_router(blend_feed_router)

# -------------------------------------------------
# ✅ ROOT
# -------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "status": "ok",
        "service": "PodBlendz API",
        "description": "Blends multiple podcasts into one audio story",
    }

