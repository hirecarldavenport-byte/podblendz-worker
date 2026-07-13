from podpal.intelligence.models import (
    ConfidenceResult,
    SupportingSource
)


# =====================================
# AUTHORITATIVE SOURCES
# =====================================

AUTHORITATIVE_SOURCES = {
    "NIH",
    "NIA",
    "CDC",
    "WHO",
    "PubMed",
    "Nature",
    "JAMA",
    "NEJM",
    "Mayo Clinic",
    "Cleveland Clinic",
    "Harvard Health",
    "Johns Hopkins",
    "Stanford Medicine",
    "NINDS",
}


# =====================================
# LABELS
# =====================================

HIGH_CONFIDENCE = "High"
SUPPORTED = "Supported"
EMERGING = "Emerging"
SPECULATIVE = "Speculative"


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
    Calculate confidence based on:

    - reputable corroborating sources
    - podcast diversity
    - supporting transcript segments
    - contradictions
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
    # PODCAST SUPPORT
    # =====================================

    score += min(podcast_count * 0.08, 0.24)

    # =====================================
    # SEGMENT SUPPORT
    # =====================================

    score += min(segment_count * 0.03, 0.21)

    # =====================================
    # CONTRADICTION PENALTY
    # =====================================

    score -= contradiction_count * 0.10

    # =====================================
    # NORMALIZATION
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
        label = HIGH_CONFIDENCE

    elif score >= 0.70:
        label = SUPPORTED

    elif score >= 0.50:
        label = EMERGING

    else:
        label = SPECULATIVE

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
    result: ConfidenceResult
):
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
# REPUTABLE RSS SOURCES
# =====================================

TRUSTED_RSS_FEEDS = {
    "nih": "https://www.nih.gov/news-events/news-releases/feed",
    "nia": "https://www.nia.nih.gov/news/rss.xml",
    "cdc": "https://tools.cdc.gov/api/v2/resources/media/rss.xml",
    "who": "https://www.who.int/rss-feeds/news-english.xml",
    "nature": "https://www.nature.com/nature.rss",
    "mayo_clinic": "https://newsnetwork.mayoclinic.org/feed/",
    "cleveland_clinic": "https://health.clevelandclinic.org/feed/",
    "harvard_health": "https://www.health.harvard.edu/blog/feed",
    "johns_hopkins": "https://hub.jhu.edu/rss/",
    "pubmed": (
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/"
    ),
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