from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute


# -------------------------------------------------
# ✅ STARTUP LOG
# -------------------------------------------------
print("✅ Loading blend routes...")

# -------------------------------------------------
# ✅ LOAD ENV
# -------------------------------------------------
load_dotenv()

# -------------------------------------------------
# ✅ PATHS
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "ui"
ASSETS_DIR = UI_DIR / "assets"
INDEX_FILE = UI_DIR / "index-v2.html"

print("✅ PodBlendz backend starting...")


# -------------------------------------------------
# ✅ APP
# -------------------------------------------------
app = FastAPI(title="PodBlendz Backend")


# -------------------------------------------------
# ✅ STATIC FILES
# -------------------------------------------------
if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(ASSETS_DIR)),
        name="assets",
    )
    print("✅ Static assets mounted")
else:
    print("⚠️ No assets directory found")


# -------------------------------------------------
# ✅ ROOT ROUTE
# -------------------------------------------------
@app.get("/", include_in_schema=False)
def homepage():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)

    return {
        "status": "PodBlendz backend running",
        "note": "UI not present in deployment",
    }


# -------------------------------------------------
# ✅ ROUTES (IMPORT AFTER APP)
# -------------------------------------------------
from podpal.routes.health import router as health_router
from podpal.routes.s3_routes import router as s3_router
from podpal.routes.narration_routes import router as narration_router
from podpal.routes.blend_routes import router as blend_router


app.include_router(health_router)
app.include_router(s3_router)
app.include_router(narration_router)
app.include_router(blend_router)


# -------------------------------------------------
# ✅ DEBUG ROUTES
# -------------------------------------------------
print("\n✅ REGISTERED ROUTES:")
for route in app.routes:
    if isinstance(route, APIRoute):
        print("➡️", route.path)
