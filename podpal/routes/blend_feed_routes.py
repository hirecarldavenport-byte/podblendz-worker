from fastapi import APIRouter

from podpal.db.database import SessionLocal

from podpal.db.blend_store import (
    get_recent_blends,
    get_blend,
    get_blend_podcasts,
    get_blend_creators,
)

router = APIRouter()


# -------------------------------------------------
# BLENDS FEED
# -------------------------------------------------

@router.get("/blends")
def list_blends():

    db = SessionLocal()

    try:

        blends = get_recent_blends(
            db,
            limit=100
        )

        results = []

        for blend in blends:

            creators = get_blend_creators(
                db,
                blend.id
            )

            podcasts = get_blend_podcasts(
                db,
                blend.id
            )

            results.append({

                "id": blend.id,

                "title": blend.title,

                "summary": blend.summary,

                "description": blend.description,

                "duration_ms": blend.duration_ms,

                "clip_count": blend.clip_count,

                "audio_file": blend.audio_file,

                "confidence_label": blend.confidence_label,

                "created_at": str(blend.created_at),

                # -------------------------------------------------
                # SOURCE ATTRIBUTION
                # -------------------------------------------------

                "creators": [
                    c.creator_name
                    for c in creators
                ],

                "podcasts": [
                    p.podcast_name
                    for p in podcasts
                ]
            })

        return results

    finally:

        db.close()


# -------------------------------------------------
# BLEND DETAIL
# -------------------------------------------------

@router.get("/blend/{blend_id}")
def blend_detail(blend_id: str):

    db = SessionLocal()

    try:

        blend = get_blend(
            db,
            blend_id
        )

        if not blend:

            return {
                "error": "Blend not found"
            }

        creators = get_blend_creators(
            db,
            blend_id
        )

        podcasts = get_blend_podcasts(
            db,
            blend_id
        )

        return {

            "id": blend.id,

            "title": blend.title,

            "summary": blend.summary,

            "description": blend.description,

            "duration_ms": blend.duration_ms,

            "clip_count": blend.clip_count,

            "audio_file": blend.audio_file,

            "confidence_label": blend.confidence_label,

            "created_at": str(blend.created_at),

            # -------------------------------------------------
            # SOURCE ATTRIBUTION
            # -------------------------------------------------

            "creators": [
                c.creator_name
                for c in creators
            ],

            "podcasts": [
                p.podcast_name
                for p in podcasts
            ]
        }

    finally:

        db.close()