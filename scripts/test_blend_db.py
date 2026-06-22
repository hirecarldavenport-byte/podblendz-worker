print("🚀 STARTING BLEND DATABASE TEST")

import uuid
from datetime import datetime, UTC

from podpal.db.database import SessionLocal
from podpal.db.blend_store import create_blend

print("✅ IMPORTS COMPLETE")

db = SessionLocal()

try:

    print("✅ DATABASE SESSION CREATED")

    metadata = {

        "id": str(uuid.uuid4()),

        "title": "AI Test Blend",

        "summary":
            "Demo blend used to validate metadata persistence.",

        "description":
            "Testing Blend storage and retrieval.",

        "query":
            "Artificial Intelligence",

        "audio_file":
            "demo.mp3",

        "image":
            "demo.jpg",

        "duration_ms":
            120000,

        "clip_count":
            25,

        "creators": [
            "Lex Fridman",
            "Diary Of A CEO"
        ],

        "podcasts": [
            "lex_fridman",
            "diary_of_a_ceo"
        ],

        "topics": [
            "AI",
            "Jobs",
            "Future Of Work"
        ],

        "confidence": {

            "score": 0.82,

            "label": "Supported",

            "corroboration_count": 4
        },

        "created_at":
            datetime.now(UTC)
    }

    print("✅ METADATA CREATED")

    blend = create_blend(
        db,
        metadata
    )

    print(
        f"✅ BLEND SAVED: {blend.id}"
    )

    print(
        f"📌 Title: {metadata['title']}"
    )

    print(
        f"🎧 Duration: {metadata['duration_ms']} ms"
    )

    print(
        f"👥 Creators: "
        f"{', '.join(metadata['creators'])}"
    )

    print(
        f"⭐ Confidence: "
        f"{metadata['confidence']['label']}"
    )

except Exception as e:

    print(
        f"❌ TEST FAILED: {e}"
    )

finally:

    db.close()

    print(
        "✅ DATABASE SESSION CLOSED"
    )

print("🎉 TEST COMPLETE")
