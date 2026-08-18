from fastapi import APIRouter, HTTPException, Header
from podpal.db.database import SessionLocal
from podpal.db.models import Blend
from podpal.db.blend_store import create_blend
from datetime import datetime


import os
import traceback

router = APIRouter()

PUBLISH_API_KEY = os.environ.get(
    "BLEND_PUBLISH_API_KEY",
    "change-me"
)


@router.post("/publish-blend")
def publish_blend(
    payload: dict,
    x_api_key: str = Header(default="")
):
    """
    Publish a completed Blend into production.

    Expected payload:

    {
        "id": "...",
        "title": "...",
        "summary": "...",
        "description": "...",
        "query": "...",
        "audio_file": "...",
        "image": "...",
        "duration_ms": 123,
        "clip_count": 30,
        "creators": [...],
        "episodes": [...],
        "podcasts": [...],
        "episode_objects": [...],
        "topics": [...],
        "confidence": {...},
        "created_at": "..."
    }
    """

    if x_api_key != PUBLISH_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    db = SessionLocal()

    try:

        blend_id = payload.get("id")

        if not blend_id:
            raise HTTPException(
                status_code=400,
                detail="Missing blend id"
            )

        existing = (
            db.query(Blend)
            .filter(
                Blend.id == blend_id
            )
            .first()
        )

        if existing:
            return {
                "success": True,
                "message": "Blend already exists",
                "id": blend_id
            }
        created_at = payload.get("created_at")
        if isinstance(created_at, str):
            payload["created_at"] = datetime.fromisoformat(
                created_at
            )

        print(payload.get("episode_objects"))

        create_blend(
            db,
            payload
        )

        print(
            f"✅ Published Blend: "
            f"{payload.get('title')}"
        )

        return {
            "success": True,
            "message": "Blend published",
            "id": blend_id
        }

    except HTTPException:
        raise

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()