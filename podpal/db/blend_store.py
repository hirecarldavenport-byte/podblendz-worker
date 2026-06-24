import uuid

from sqlalchemy.orm import Session

from podpal.db.models import (
    Blend,
    BlendCreator,
    BlendPodcast,
    BlendTopic
)


# =====================================
# CREATE
# =====================================

def create_blend(
    db: Session,
    metadata: dict
):
    """
    Persist a generated blend.

    Returns:
        Blend
    """

    blend = Blend(

        id=metadata["id"],

        title=metadata.get(
            "title"
        ),

        summary=metadata.get(
            "summary"
        ),

        description=metadata.get(
            "description"
        ),

        query=metadata.get(
            "query"
        ),

        audio_file=metadata.get(
            "audio_file"
        ),

        image=metadata.get(
            "image"
        ),

        duration_ms=metadata.get(
            "duration_ms",
            0
        ),

        clip_count=metadata.get(
            "clip_count",
            0
        ),

        confidence_score=str(
            metadata.get(
                "confidence",
                {}
            ).get(
                "score",
                0
            )
        ),

        confidence_label=
        metadata.get(
            "confidence",
            {}
        ).get(
            "label",
            "Unknown"
        ),

        corroboration_count=
        metadata.get(
            "confidence",
            {}
        ).get(
            "corroboration_count",
            0
        ),

        created_at=metadata.get(
            "created_at"
        )
    )

    db.add(blend)

    # =========================
    # CREATORS
    # =========================

    for creator in metadata.get(
        "creators",
        []
    ):

        db.add(

            BlendCreator(
                id=str(
                    uuid.uuid4()
                ),

                blend_id=blend.id,

                creator_name=creator
            )
        )

    # =========================
    # PODCASTS
    # =========================

    for podcast in metadata.get(
        "podcasts",
        []
    ):

        db.add(

            BlendPodcast(
                id=str(
                    uuid.uuid4()
                ),

                blend_id=blend.id,

                podcast_name=podcast
            )
        )

    # =========================
    # TOPICS
    # =========================

    for topic in metadata.get(
        "topics",
        []
    ):

        db.add(

            BlendTopic(
                id=str(
                    uuid.uuid4()
                ),

                blend_id=blend.id,

                topic=topic
            )
        )

    try:

        db.commit()

        db.refresh(blend)

        return blend

    except Exception:

        db.rollback()

        raise


# =====================================
# READ
# =====================================

def get_blend(
    db: Session,
    blend_id: str
):

    return (
        db.query(Blend)
        .filter(
            Blend.id == blend_id
        )
        .first()
    )


def get_all_blends(
    db: Session
):

    return (

        db.query(Blend)

        .order_by(
            Blend.created_at.desc()
        )

        .all()
    )


def get_recent_blends(
    db: Session,
    limit: int = 25
):

    return (

        db.query(Blend)

        .order_by(
            Blend.created_at.desc()
        )

        .limit(limit)

        .all()
    )


# =====================================
# SEARCH
# =====================================

def search_blends(
    db: Session,
    query: str
):

    return (

        db.query(Blend)

        .filter(
            Blend.title.ilike(
                f"%{query}%"
            )
        )

        .all()
    )


# =====================================
# STATS
# =====================================

def count_blends(
    db: Session
):

    return (

        db.query(Blend)

        .count()
    )


# =====================================
# DELETE
# =====================================

def delete_blend(
    db: Session,
    blend_id: str
):
    """
    Delete a blend and all related records.
    """

    db.query(
        BlendCreator
    ).filter(
        BlendCreator.blend_id == blend_id
    ).delete()

    db.query(
        BlendPodcast
    ).filter(
        BlendPodcast.blend_id == blend_id
    ).delete()

    db.query(
        BlendTopic
    ).filter(
        BlendTopic.blend_id == blend_id
    ).delete()

    blend = get_blend(
        db,
        blend_id
    )

    if not blend:
        return False

    db.delete(blend)

    db.commit()

    return True