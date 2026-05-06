"""
Master Topic Podcasters
-----------------------

Canonical editorial registry of podcasters grouped by master topic.

This file is AUTHORITATIVE:
- All ingestion eligibility flows from here
- media_access explicitly governs whether audio may be downloaded
- source_quality indicates system trust level
"""

from typing import Dict, List, Optional, TypedDict


# =================================================
# STRICT CANONICAL PODCASTER TYPE
# =================================================

class CanonicalPodcaster(TypedDict):
    id: str
    name: str

    ingestible: bool

    # Editorial controls
    primary_topic: str
    allow_cross_topic: bool

    # Ingestion controls
    feed_url: Optional[str]
    media_access: str  # "direct" | "blocked"

    # System control
    source_quality: str  # "core" | "experimental" | "blocked"


# =================================================
# MASTER PODCAST REGISTRY
# =================================================

TOP_PODCASTERS_BY_MASTER_TOPIC: Dict[str, List[CanonicalPodcaster]] = {

    # =================================================
    # CORE BLENDZ (YOUR FOUNDATION)
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
            "id": "you_are_not_so_smart",
            "name": "You Are Not So Smart",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "direct",
            "source_quality": "core",
        },
        {
            "id": "rationally_speaking",
            "name": "Rationally Speaking",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": True,
            "feed_url": "https://rationallyspeakingpodcast.org/feed/podcast/",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # SCIENCE EXPANSION (CLEAN + RELIABLE)
    # =================================================
    "science_general": [
        {
            "id": "big_biology",
            "name": "Big Biology",
            "ingestible": True,
            "primary_topic": "science_general",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "direct",
            "source_quality": "core",
        },
        {
            "id": "naked_scientists",
            "name": "The Naked Scientists",
            "ingestible": True,
            "primary_topic": "science_general",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "direct",
            "source_quality": "core",
        },
        {
            "id": "ologies",
            "name": "Ologies",
            "ingestible": False,
            "primary_topic": "science_general",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.megaphone.fm/ologies",
            "media_access": "blocked",
            "source_quality": "blocked",
        },
        {
            "id": "science_vs",
            "name": "Science Vs",
            "ingestible": False,
            "primary_topic": "science_general",
            "allow_cross_topic": False,
            "feed_url": "https://feeds.megaphone.fm/science-vs",
            "media_access": "blocked",
            "source_quality": "blocked",
        },
    ],

    # =================================================
    # GENETICS
    # =================================================
    "genetics": [
        {
            "id": "genetics_unzipped",
            "name": "Genetics Unzipped",
            "ingestible": True,
            "primary_topic": "genetics",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # FINANCE / CULTURAL FINANCE
    # =================================================
    "finance": [
        {
            "id": "earn_your_leisure",
            "name": "Earn Your Leisure",
            "ingestible": True,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": None,
            "media_access": "direct",  # tested but routed
            "source_quality": "experimental",
        },
        {
            "id": "freakonomics_radio",
            "name": "Freakonomics Radio",
            "ingestible": True,
            "primary_topic": "finance",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/Y8lFbOT4",
            "media_access": "direct",
            "source_quality": "core",
        },
    ],

    # =================================================
    # EDUCATION & LEARNING
    # =================================================
    "education_learning": [
        {
            "id": "hidden_brain",
            "name": "Hidden Brain",
            "ingestible": True,
            "primary_topic": "education_learning",
            "allow_cross_topic": False,
            "feed_url": "https://feeds.npr.org/510308/podcast.xml",
            "media_access": "direct",
            "source_quality": "experimental",
        },
        {
            "id": "ted_talks_daily",
            "name": "TED Talks Daily",
            "ingestible": False,
            "primary_topic": "education_learning",
            "allow_cross_topic": False,
            "feed_url": None,
            "media_access": "blocked",
            "source_quality": "blocked",
        },
    ],

    # =================================================
    # MEDIA / CULTURE (NON-INGESTABLE BUT IMPORTANT)
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
# FAIL-SOFT ITERATOR
# =================================================

def iter_ingestible_podcasters():
    for topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():
        for podcaster in podcasters:
            if podcaster.get("ingestible") and podcaster.get("media_access") == "direct":
                yield topic, podcaster