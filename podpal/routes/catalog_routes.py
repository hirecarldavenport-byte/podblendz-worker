from fastapi import APIRouter
import sqlite3

router = APIRouter(tags=["Catalog"])

DB_PATH = "podblendz.db"


@router.get("/podcasts")
def list_podcasts():

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT
            podcast_id,
            COUNT(*) as episode_count
        FROM episodes
        GROUP BY podcast_id
        ORDER BY episode_count DESC
        """
    ).fetchall()

    conn.close()

    return [
        {
            "podcast_id": row[0],
            "episode_count": row[1]
        }
        for row in rows
    ]


@router.get("/episodes")
def list_episodes(limit: int = 100):

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            id,
            podcast_id,
            title,
            published_at,
            audio_s3_key,
            transcript_status
        FROM episodes
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]