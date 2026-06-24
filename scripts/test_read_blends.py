from podpal.db.database import (
    SessionLocal
)

from podpal.db.blend_store import (
    get_all_blends
)

db = SessionLocal()

try:

    blends = get_all_blends(
        db
    )

    print(
        f"\nBlend Count: {len(blends)}"
    )

    for blend in blends:

        print(
            f"\n{blend.title}"
        )

        print(
            f"Duration: {blend.duration_ms}"
        )

        print(
            f"Audio: {blend.audio_file}"
        )

finally:

    db.close()