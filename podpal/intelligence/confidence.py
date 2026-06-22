from podpal.intelligence.models import (
    ConfidenceResult,
    SupportingSource
)


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
    supporting_sources: list[SupportingSource]
) -> ConfidenceResult:
    """
    Generate a confidence score based on
    external corroboration sources.

    Parameters
    ----------
    supporting_sources : list[SupportingSource]

    Returns
    -------
    ConfidenceResult
    """

    corroboration_count = len(
        supporting_sources
    )

    # =========================
    # HIGH
    # =========================

    if corroboration_count >= 5:

        score = 0.90

        return ConfidenceResult(
            score=score,
            label=HIGH_CONFIDENCE,
            corroboration_count=corroboration_count,
            sources=supporting_sources
        )

    # =========================
    # SUPPORTED
    # =========================

    if corroboration_count >= 3:

        score = 0.75

        return ConfidenceResult(
            score=score,
            label=SUPPORTED,
            corroboration_count=corroboration_count,
            sources=supporting_sources
        )

    # =========================
    # EMERGING
    # =========================

    if corroboration_count >= 1:

        score = 0.60

        return ConfidenceResult(
            score=score,
            label=EMERGING,
            corroboration_count=corroboration_count,
            sources=supporting_sources
        )

    # =========================
    # SPECULATIVE
    # =========================

    return ConfidenceResult(
        score=0.40,
        label=SPECULATIVE,
        corroboration_count=0,
        sources=[]
    )


# =====================================
# UI HELPERS
# =====================================

def confidence_badge(
    result: ConfidenceResult
):
    """
    Simple UI-friendly text.
    """

    return (
        f"{result.label} Confidence "
        f"({result.corroboration_count} sources)"
    )


# =====================================
# METADATA
# =====================================

def confidence_metadata(
    result: ConfidenceResult
):
    """
    Convert to JSON-friendly metadata.
    """

    return {
        "score": round(
            result.score,
            2
        ),

        "label": result.label,

        "corroboration_count":
            result.corroboration_count,

        "supporting_sources": [

            {
                "source": s.source,
                "title": s.title,
                "url": s.url,
                "score": s.score
            }

            for s in result.sources
        ]
    }


# =====================================
# TEST
# =====================================

if __name__ == "__main__":

    test_sources = [

        SupportingSource(
            source="NIH",
            title="Sleep and Dementia",
            url="https://example.com",
            score=0.92
        ),

        SupportingSource(
            source="CDC",
            title="Brain Health",
            url="https://example.com",
            score=0.88
        ),

        SupportingSource(
            source="Nature",
            title="Cognitive Decline",
            url="https://example.com",
            score=0.84
        ),
    ]

    result = calculate_confidence(
        test_sources
    )

    print(
        confidence_badge(result)
    )

    print(
        confidence_metadata(result)
    )