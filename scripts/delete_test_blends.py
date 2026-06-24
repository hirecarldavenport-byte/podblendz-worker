from podpal.db.database import (
    SessionLocal
)

from podpal.db.blend_store import (
    get_all_blends,
    delete_blend
)

db = SessionLocal()

try:

    blends = get_all_blends(db)

    for blend in blends:

        if blend.title == "AI Test Blend":

            delete_blend(
                db,
                blend.id
            )

            print(
                f"Deleted: {blend.id}"
            )

finally:

    db.close()