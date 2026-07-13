from fastapi import APIRouter
import sqlite3

router = APIRouter(tags=["Catalog"])

DB_PATH = "podblendz.db"


@router.get("/podcasts")
def list_podcasts():

    conn = sqlite3.connect(DB_PATH)

    try:

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

        return [
            {
                "podcast_id": row[0],
                "episode_count": row[1]
            }
            for row in rows
        ]

    finally:
        conn.close()


@router.get("/episodes")
def list_episodes(
    limit: int = 100,
    offset: int = 0,
    podcast_id: str | None = None,
    real_titles_only: bool = False,
):

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:

        query = """
        SELECT
            id,
            podcast_id,
            title,
            published_at,
            audio_s3_key,
            transcript_status
        FROM episodes
        WHERE 1=1
        """

        params = []

        if podcast_id:
            query += """
            AND podcast_id = ?
            """
            params.append(podcast_id)

        if real_titles_only:
            query += """
            AND title IS NOT NULL
            AND TRIM(title) != ''
            AND title != id
            """

        query += """
        ORDER BY updated_at DESC
        LIMIT ?
        OFFSET ?
        """

        params.extend([limit, offset])

        rows = conn.execute(
            query,
            params
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


@router.get("/catalog/stats")
def catalog_stats():

    conn = sqlite3.connect(DB_PATH)

    try:

        total_episodes = conn.execute(
            """
            SELECT COUNT(*)
            FROM episodes
            """
        ).fetchone()[0]

        total_podcasts = conn.execute(
            """
            SELECT COUNT(DISTINCT podcast_id)
            FROM episodes
            """
        ).fetchone()[0]

        real_titles = conn.execute(
            """
            SELECT COUNT(*)
            FROM episodes
            WHERE title IS NOT NULL
            AND TRIM(title) != ''
            AND title != id
            """
        ).fetchone()[0]

        placeholder_titles = conn.execute(
            """
            SELECT COUNT(*)
            FROM episodes
            WHERE title = id
            """
        ).fetchone()[0]

        transcript_completed = conn.execute(
            """
            SELECT COUNT(*)
            FROM episodes
            WHERE transcript_status = 'completed'
            """
        ).fetchone()[0]

        transcript_pending = conn.execute(
            """
            SELECT COUNT(*)
            FROM episodes
            WHERE transcript_status = 'pending'
            """
        ).fetchone()[0]

        metadata_coverage_pct = round(
            (real_titles / total_episodes) * 100,
            2
        ) if total_episodes else 0

        return {
            "episodes": total_episodes,
            "podcasts": total_podcasts,
            "episodes_with_real_titles": real_titles,
            "episodes_with_placeholder_titles": placeholder_titles,
            "metadata_coverage_pct": metadata_coverage_pct,
            "transcript_completed": transcript_completed,
            "transcript_pending": transcript_pending,
        }

    finally:
        conn.close()