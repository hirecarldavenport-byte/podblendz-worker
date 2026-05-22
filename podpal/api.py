from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# -------------------------------------------------
# ✅ Resolve project root correctly
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"

# ✅ Debug (optional)
print("✅ Static audio directory:", AUDIO_DIR)
print("✅ Exists:", AUDIO_DIR.exists())

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
# ✅ STATIC AUDIO SERVING (FIXED)
# -------------------------------------------------

# IMPORTANT: Serves /audio/final/*.mp3 correctly
app.mount(
    "/audio",
    StaticFiles(directory=str(AUDIO_DIR), html=False),
    name="audio"
)

print("✅ Static assets mounted")

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
