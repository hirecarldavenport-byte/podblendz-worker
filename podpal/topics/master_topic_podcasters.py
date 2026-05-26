"""
master_topic_podcasters.py

✅ Master ingestion registry
✅ Safe ingestion only (direct RSS feeds)
✅ Typed + structured for ingestion pipelines
"""

from typing import Dict, List, Optional, TypedDict


# =================================================
# ✅ TYPE DEFINITION
# =================================================

class CanonicalPodcaster(TypedDict):
    id: str
    name: str

    ingestible: bool

    primary_topic: str
    allow_cross_topic: bool

    feed_url: Optional[str]
    media_access: str  # "direct" | "blocked"

    source_quality: str  # "core" | "experimental"


# =================================================
# ✅ MASTER REGISTRY
# =================================================

TOP_PODCASTERS_BY_MASTER_TOPIC: Dict[str, List[CanonicalPodcaster]] = {

    # =================================================
    # 🧠 CORE THINKING
    # =================================================
    "core_blendz": [
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
        {
            "id": "as_a_man_readeth",
            "name": "As a Man Readeth (LibriVox)",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://librivox.org/rss/452",
            "media_access": "direct",
            "source_quality": "core",
        },
        {
            "id": "hidden_brain",
            "name": "Hidden Brain",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.npr.org/510308/podcast.xml",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # 🧬 SCIENCE
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
            "id": "the_drive",
            "name": "The Drive (Peter Attia)",
            "ingestible": True,
            "primary_topic": "science_general",
            "allow_cross_topic": True,
            "feed_url": "https://peterattiamd.com/feed/podcast/",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # 💰 ECONOMICS
    # =================================================
    "finance": [
        {
            "id": "planet_money",
            "name": "Planet Money",
            "ingestible": True,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.npr.org/510289/podcast.xml",
            "media_access": "direct",
            "source_quality": "core",
        },
        {
            "id": "indicator",
            "name": "The Indicator",
            "ingestible": True,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.npr.org/510325/podcast.xml",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # 🧠 PSYCHOLOGY
    # =================================================
    "education_learning": [
        {
            "id": "therapy_black_girls",
            "name": "Therapy for Black Girls",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/tb7MZdl7",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # 🎭 CULTURE
    # =================================================
    "media_culture": [
        {
            "id": "code_switch",
            "name": "Code Switch",
            "ingestible": True,
            "primary_topic": "media_culture",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.npr.org/510312/podcast.xml",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],
}


# =================================================
# ✅ SAFE ITERATOR (CRITICAL)
# =================================================

def iter_ingestible_podcasters():
    """Yield only valid ingestible feeds"""

    for topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():
        for podcaster in podcasters:
            if (
                podcaster.get("ingestible")
                and podcaster.get("media_access") == "direct"
                and podcaster.get("feed_url")
            ):
                yield topic, podcaster





