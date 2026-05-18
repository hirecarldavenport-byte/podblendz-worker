from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ✅ Load env
load_dotenv()

# ✅ Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "ui"
ASSETS_DIR = UI_DIR / "assets"
INDEX_FILE = UI_DIR / "index-v2.html"

print("✅ PodBlendz backend starting...")  # helpful for logs

# ✅ App
app = FastAPI(title="PodBlendz Backend")

# ✅ Mount assets ONLY if directory exists
if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(ASSETS_DIR)),
        name="assets",
    )
    print("✅ Static assets mounted")
else:
    print("⚠️ No assets directory found")

# ✅ SAFE HOMEPAGE (CRITICAL FIX)
@app.get("/", include_in_schema=False)
def homepage():

    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)

    # ✅ fallback so server doesn't crash
    return {
        "status": "PodBlendz backend running",
        "note": "UI not present in deployment",
    }


# ✅ API ROUTES (import AFTER app creation for safety)
from podpal.routes.health import router as health_router
from podpal.routes.s3_routes import router as s3_router
from podpal.routes.narration_routes import router as narration_router
from podpal.routes.blend_routes import router as blend_router

app.include_router(health_router)
app.include_router(s3_router)
app.include_router(narration_router)
app.include_router(blend_router)
