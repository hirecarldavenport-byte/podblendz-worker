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
            "id": "diary_of_a_ceo",
            "name": "The Diary Of A CEO",
            "ingestible": True,
            "primary_topic": "entrepreneurship",
            "allow_cross_topic": True,
            "feed_url": "https://api.substack.com/feed/podcast/8155644.rss",
            "media_access": "direct",
            "source_quality": "core",
        },

        {
            "id": "the_daily",
            "name": "The Daily",
            "ingestible": True,
            "primary_topic": "news_politics",
            "allow_cross_topic": True,
            "feed_url": "https://feeds.simplecast.com/54nAGcIl",
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

                
    
                {
                    "id": "ted_talks_daily",
                    "name": "TED Talks Daily",
                    "ingestible": True,
                    "primary_topic": "ideas_education",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.feedburner.com/TEDTalks_audio",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "npr_politics",
                    "name": "NPR Politics Podcast",
                    "ingestible": True,
                    "primary_topic": "news_politics",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.npr.org/510310/podcast.xml",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "short_wave",
                    "name": "Short Wave",
                    "ingestible": True,
                    "primary_topic": "science",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.npr.org/510351/podcast.xml",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "pod_save_america",
                    "name": "Pod Save America",
                    "ingestible": True,
                    "primary_topic": "news_politics",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.simplecast.com/4Mvg7cFf",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "life_kit",
                    "name": "Life Kit",
                    "ingestible": True,
                    "primary_topic": "lifestyle",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.npr.org/510338/podcast.xml",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "startalk",
                    "name": "StarTalk Radio",
                    "ingestible": True,
                    "primary_topic": "science_space",
                    "allow_cross_topic": True,
                    "feed_url": "https://www.startalkradio.net/feed/startalk-all-podcasts/",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "benjamin_dixon",
                    "name": "The Benjamin Dixon Show",
                    "ingestible": True,
                    "primary_topic": "news_politics",
                    "allow_cross_topic": True,
                    "feed_url": "https://benjamindixonshow.libsyn.com/rss",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "the_big_picture",
                    "name": "The Big Picture",
                    "ingestible": True,
                    "primary_topic": "film_tv",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/thebigpicture",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "freakonomics_radio",
                    "name": "Freakonomics Radio",
                    "ingestible": True,
                    "primary_topic": "economics_business",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/freakonomics",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "how_i_built_this",
                    "name": "How I Built This",
                    "ingestible": True,
                    "primary_topic": "business_entrepreneurship",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.npr.org/510313/podcast.xml",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "higher_learning",
                    "name": "Higher Learning",
                    "ingestible": True,
                    "primary_topic": "culture_education",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/higherlearning",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "switched_on_pop",
                    "name": "Switched on Pop",
                    "ingestible": True,
                    "primary_topic": "music_pop",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.simplecast.com/switchedonpop",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "ologies",
                    "name": "Ologies",
                    "ingestible": True,
                    "primary_topic": "science",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/ologies",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "up_first",
                    "name": "Up First",
                    "ingestible": True,
                    "primary_topic": "news_morning",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.npr.org/510318/podcast.xml",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "ezra_klein_show",
                    "name": "The Ezra Klein Show",
                    "ingestible": True,
                    "primary_topic": "news_politics",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.simplecast.com/ezraklein",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "dna_today",
                    "name": "DNA Today",
                    "ingestible": True,
                    "primary_topic": "science_genetics",
                    "allow_cross_topic": True,
                    "feed_url": "https://dnatoday.libsyn.com/rss",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "dissect",
                    "name": "Dissect",
                    "ingestible": True,
                    "primary_topic": "music_analysis",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/dissect",
                    "media_access": "direct",
                    "source_quality": "core"
                },
                {
                    "id": "science_vs",
                    "name": "Science Vs",
                    "ingestible": True,
                    "primary_topic": "science",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/sciencevs",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "all_songs_considered",
                    "name": "All Songs Considered",
                    "ingestible": True,
                    "primary_topic": "music_all",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.npr.org/510019/podcast.xml",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "gastropod",
                    "name": "Gastropod",
                    "ingestible": True,
                    "primary_topic": "food_science",
                    "allow_cross_topic": True,
                    "feed_url": "https://gastropod.com/feed/podcast/",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "the_sporkful",
                    "name": "The Sporkful",
                    "ingestible": True,
                    "primary_topic": "food_culture",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/thesporkful",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "jemele_hill",
                    "name": "Jemele Hill Is Unbothered",
                    "ingestible": True,
                    "primary_topic": "sports_culture",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.megaphone.fm/jemelehill",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "serial",
                    "name": "Serial",
                    "ingestible": True,
                    "primary_topic": "true_crime",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.serialpodcast.org/serialpodcast",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "filmspotting",
                    "name": "Filmspotting",
                    "ingestible": True,
                    "primary_topic": "film_review",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.filmspotting.net/filmspotting",
                    "media_access": "direct",
                    "source_quality": "core",
                },
                {
                    "id": "in_the_dark",
                    "name": "In the Dark",
                    "ingestible": True,
                    "primary_topic": "true_crime_investigative",
                    "allow_cross_topic": True,
                    "feed_url": "https://feeds.apm.org/in-the-dark",
                    "media_access": "direct",
                    "source_quality": "core",
                },
             
                
                {
                    "id": "kevonstage_not_my_best_moment",
                    "name": "Not My Best Moment with KevOnStage",
                    "ingestible": True,
                    "primary_topic": "literature_culture",
                    "allow_cross_topic": True,
                    "feed_url": "https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/ed96ed15-e1a5-40a6-9e19-b386014b76d5/ecbf132e-df53-49a5-aee0-b386014b7a9f/podcast.rss",
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