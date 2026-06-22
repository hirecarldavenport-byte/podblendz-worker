print("STARTING TEST")

import uuid
from datetime import datetime

from podpal.db.database import SessionLocal
from podpal.db.blend_store import create_blend

print("IMPORTS COMPLETE")

db = SessionLocal()

print("SESSION CREATED")

metadata = {
    "id": str(uuid.uuid4()),
    "title": "AI Test Blend",
    "summary": "Test",
    "description": "Test",
    "query": "AI",
    "audio_file": "demo.mp3",
    "image": "demo.jpg",
    "duration_ms": 1000,
    "clip_count": 1,
    "creators": ["Lex Fridman"],
    "podcasts": ["lex_fridman"],
    "topics": ["AI"],
    "confidence": {
        "score": 0.8,
        "label": "Supported",
        "corroboration_count": 3,
    },
    "created_at": datetime.utcnow()
}

print("METADATA CREATED")

blend = create_blend(
    db,
    metadata
)

print(
    f"✅ Blend Saved: {blend.id}"
)

db.close()

print("DONE")