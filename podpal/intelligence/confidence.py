from podpal.intelligence.models import (
    ConfidenceResult,
    SupportingSource,
)


# =====================================
# AUTHORITATIVE SOURCES
# =====================================

AUTHORITATIVE_SOURCES = {
    # Health / Medicine
    "NIH",
    "NIA",
    "NINDS",
    "PubMed",
    "CDC",
    "WHO",
    "Mayo Clinic",
    "Cleveland Clinic",
    "Johns Hopkins",
    "Harvard Health",
    "Stanford Medicine",
    "The Lancet",
    "JAMA",
    "NEJM",

    # Science
    "Nature",
    "Science",

    # Business / Strategy
    "McKinsey",
    "Deloitte Insights",
    "Harvard Business Review",
    "MIT Sloan",
    "Brookings",

    # Economics / Policy
    "Federal Reserve",
    "World Bank",
    "IMF",
    "OECD",
    "BLS",
    "CBO",

    # AI / Research
    "OpenAI Research",
    "Google Research",
    "DeepMind",
    "Anthropic Research",
    "Stanford HAI",
    "MIT CSAIL",
    "arXiv",
}


# =====================================
# LABELS
# =====================================

VERIFIED = "Verified"
SUPPORTED = "Supported"
EMERGING = "Emerging"
UNVERIFIED = "Unverified"


# =====================================
# SCORE CALCULATION
# =====================================

def calculate_confidence(
    supporting_sources: list[SupportingSource],
    podcast_count: int,
    segment_count: int,
    contradiction_count: int,
) -> ConfidenceResult:
    """
    Confidence is determined by:

    - Authoritative corroboration sources
    - Number of supporting podcasts
    - Number of supporting transcript segments
    - Contradiction penalties
    """

    corroboration_count = len(supporting_sources)

    authoritative_count = sum(
        1
        for source in supporting_sources
        if source.source in AUTHORITATIVE_SOURCES
    )

    score = 0.0

    # =====================================
    # AUTHORITATIVE SOURCES
    # =====================================

    score += min(authoritative_count * 0.15, 0.45)

    # =====================================
    # PODCAST CONSENSUS
    # =====================================

    score += min(podcast_count * 0.08, 0.24)

    # =====================================
    # SEGMENT SUPPORT
    # =====================================

    score += min(segment_count * 0.03, 0.21)

    # =====================================
    # CONTRADICTIONS
    # =====================================

    score -= contradiction_count * 0.10

    # =====================================
    # NORMALIZE
    # =====================================

    score = max(0.0, min(score, 1.0))

    # =====================================
    # LABEL
    # =====================================

    if (
        score >= 0.85
        and podcast_count >= 3
        and contradiction_count == 0
    ):
        label = VERIFIED

    elif score >= 0.70:
        label = SUPPORTED

    elif score >= 0.50:
        label = EMERGING

    else:
        label = UNVERIFIED

    return ConfidenceResult(
        score=score,
        label=label,
        corroboration_count=corroboration_count,
        sources=supporting_sources,
    )


# =====================================
# UI HELPERS
# =====================================

def confidence_badge(
    result: ConfidenceResult,
) -> str:
    return (
        f"{result.label} Confidence "
        f"({result.corroboration_count} sources)"
    )


# =====================================
# METADATA
# =====================================

def confidence_metadata(
    result: ConfidenceResult,
    podcast_count: int,
    segment_count: int,
    contradiction_count: int,
):
    return {
        "score": round(result.score, 2),
        "label": result.label,
        "corroboration_count": result.corroboration_count,
        "podcast_count": podcast_count,
        "segment_count": segment_count,
        "contradiction_count": contradiction_count,
        "supporting_sources": [
            {
                "source": s.source,
                "title": s.title,
                "url": s.url,
                "score": s.score,
            }
            for s in result.sources
        ],
    }


# =====================================
# TRUSTED RSS FEEDS
# =====================================

TRUSTED_RSS_FEEDS = {
    # Health
    "nih": "https://www.nih.gov/news-events/news-releases/feed",
    "nia": "https://www.nia.nih.gov/news/rss.xml",
    "cdc": "https://tools.cdc.gov/api/v2/resources/media/rss.xml",
    "who": "https://www.who.int/rss-feeds/news-english.xml",
    "mayo_clinic": "https://newsnetwork.mayoclinic.org/feed/",
    "cleveland_clinic": "https://health.clevelandclinic.org/feed/",
    "harvard_health": "https://www.health.harvard.edu/blog/feed",
    "johns_hopkins": "https://hub.jhu.edu/rss/",
    "pubmed": "https://pubmed.ncbi.nlm.nih.gov/rss/search/",

    # Science
    "nature": "https://www.nature.com/nature.rss",

    # Economics / Policy
    "federal_reserve":
        "https://www.federalreserve.gov/feeds/press_all.xml",

    "world_bank":
        "https://www.worldbank.org/en/news/all/rss",

    "imf":
        "https://www.imf.org/en/News/rss",

    "oecd":
        "https://www.oecd.org/newsroom/rss.xml",

    "bls":
        "https://www.bls.gov/feed/bls_latest.rss",

    # AI / Research
    "openai":
        "https://openai.com/blog/rss.xml",

    "google_research":
        "https://research.google/blog/rss/",

    "deepmind":
        "https://deepmind.google/discover/blog/rss.xml",

    "anthropic":
        "https://www.anthropic.com/news/rss.xml",

    "mit_csail":
        "https://www.csail.mit.edu/news/rss.xml",
}


# =====================================
# TEST
# =====================================

if __name__ == "__main__":

    test_sources = [
        SupportingSource(
            source="NIH",
            title="Sleep and Dementia",
            url="https://www.nih.gov",
            score=0.92,
        ),
        SupportingSource(
            source="CDC",
            title="Brain Health",
            url="https://www.cdc.gov",
            score=0.88,
        ),
        SupportingSource(
            source="Nature",
            title="Cognitive Decline",
            url="https://www.nature.com",
            score=0.84,
        ),
        SupportingSource(
            source="OpenAI Research",
            title="Reasoning Models",
            url="https://openai.com/research",
            score=0.95,
        ),
    ]

    result = calculate_confidence(
        supporting_sources=test_sources,
        podcast_count=4,
        segment_count=12,
        contradiction_count=0,
    )

    print(confidence_badge(result))

    print(
        confidence_metadata(
            result=result,
            podcast_count=4,
            segment_count=12,
            contradiction_count=0,
        )
    )