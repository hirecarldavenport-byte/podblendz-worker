"""
Master Topic Podcasters
-----------------------

Canonical editorial registry of podcasters grouped by master topic.

This file is AUTHORITATIVE:
- All ingestion eligibility flows from here
- media_access governs ingestion
- only DIRECT audio feeds should run through pipeline
"""

from typing import Dict, List, Optional, TypedDict


# =================================================
# TYPE DEFINITION
# =================================================

class CanonicalPodcaster(TypedDict):
    id: str
    name: str

    ingestible: bool

    primary_topic: str
    allow_cross_topic: bool

    feed_url: Optional[str]
    media_access: str  # "direct" | "blocked"

    source_quality: str  # "core" | "experimental" | "blocked"


# =================================================
# MASTER REGISTRY
# =================================================

TOP_PODCASTERS_BY_MASTER_TOPIC: Dict[str, List[CanonicalPodcaster]] = {

    # =================================================
    # 🧠 CORE BLENDZ FOUNDATION (HIGH SIGNAL)
    # =================================================
    "core_blendz": [

        # ✅ Already working
        {
            "id": "econtalk",
            "name": "EconTalk",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/wgl4xEgL",
            "media_access": "direct",
            "source_quality": "core",
        },

        # ✅ Strong reasoning content
        {
            "id": "knowledge_project",
            "name": "The Knowledge Project",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/ClmzXJj7",
            "media_access": "direct",
            "source_quality": "core",
        },

        {
            "id": "invest_like_the_best",
            "name": "Invest Like the Best",
            "ingestible": True,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/4T39_jAj",
            "media_access": "direct",
            "source_quality": "core",
        },

        {
            "id": "acquired",
            "name": "Acquired",
            "ingestible": True,
            "primary_topic": "business_strategy",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/i2yC1nFQ",
            "media_access": "direct",
            "source_quality": "core",
        },

        {
            "id": "my_first_million",
            "name": "My First Million",
            "ingestible": True,
            "primary_topic": "business",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/0M0F0QSn",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],


    # =================================================
    # 🧬 SCIENCE / HUMAN PERFORMANCE
    # =================================================
    "science_general": [

        {
            "id": "huberman_lab",
            "name": "Huberman Lab Podcast",
            "ingestible": True,
            "primary_topic": "science_general",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.libsyn.com/204095/rss",
            "media_access": "direct",
            "source_quality": "core",
        },

        {
            "id": "big_biology",
            "name": "Big Biology",
            "ingestible": True,
            "primary_topic": "science_general",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/XFJZy2r3",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],


    # =================================================
    # 💰 FINANCE (INCLUDING CULTURAL RELEVANCE)
    # =================================================
    "finance": [

        # ✅ culturally relevant
        {
            "id": "earn_your_leisure",
            "name": "Earn Your Leisure",
            "ingestible": True,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "direct",  # route-check required
            "source_quality": "experimental",
        },

        # ❌ blocked due to redirects
        {
            "id": "freakonomics_radio",
            "name": "Freakonomics Radio",
            "ingestible": False,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/Y8lFbOT4",
            "media_access": "blocked",
            "source_quality": "blocked",
        },
    ],


    # =================================================
    # 📚 EDUCATION / THINKING
    # =================================================
    "education_learning": [

        # ✅ public domain philosophy
        {
            "id": "as_a_man_thinketh",
            "name": "As a Man Thinketh (LibriVox)",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://librivox.org/rss/452",
            "media_access": "direct",
            "source_quality": "core",
        },

        # ⚠️ verify first (NPR systems vary)
        {
            "id": "hidden_brain",
            "name": "Hidden Brain",
            "ingestible": False,
            "primary_topic": "education_learning",
            "allow_cross_topic": False,
            "feed_url": "https://feeds.npr.org/510308/podcast.xml",
            "media_access": "blocked",
            "source_quality": "experimental",
        },
    ],


    # =================================================
    # 🎭 CULTURE / IDEAS (NON-INGEST BUT IMPORTANT)
    # =================================================
    "media_culture": [

        {
            "id": "higher_learning",
            "name": "Higher Learning",
            "ingestible": False,
            "primary_topic": "media_culture",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "blocked",
            "source_quality": "blocked",
        }
    ],
}


# =================================================
# SAFE ITERATOR
# =================================================

def iter_ingestible_podcasters():
    """Yield only clean, direct-ingestible feeds"""

    for topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():
        for podcaster in podcasters:
            if (
                podcaster.get("ingestible") and
                podcaster.get("media_access") == "direct" and
                podcaster.get("feed_url")
            ):
                yield topic, podcaster