from difflib import SequenceMatcher

from podpal.intelligence.models import (
    SupportingSource
)


# =====================================
# SIMILARITY
# =====================================

def similarity(text_a, text_b):
    """
    Simple text similarity score.

    Returns:
        float between 0 and 1
    """

    return SequenceMatcher(
        None,
        text_a.lower(),
        text_b.lower()
    ).ratio()


# =====================================
# MATCH RSS ARTICLES
# =====================================

def find_supporting_sources(
    segment_text,
    articles,
    threshold=0.50,
    max_results=10
):
    """
    Find RSS articles that support
    a podcast segment.

    Parameters
    ----------
    segment_text : str

    articles : list[dict]

    threshold : float

    max_results : int
    """

    matches = []

    if not segment_text:
        return matches

    for article in articles:

        title = article.get(
            "title",
            ""
        )

        summary = article.get(
            "summary",
            ""
        )

        article_text = (
            f"{title} {summary}"
        )

        if not article_text.strip():
            continue

        score = similarity(
            segment_text,
            article_text
        )

        if score >= threshold:

            matches.append(

                SupportingSource(
                    source=article.get(
                        "source",
                        "Unknown"
                    ),

                    title=title,

                    url=article.get(
                        "url",
                        ""
                    ),

                    score=round(
                        score,
                        3
                    )
                )
            )

    matches.sort(
        key=lambda x: x.score,
        reverse=True
    )

    return matches[:max_results]


# =====================================
# SUMMARY REPORT
# =====================================

def get_corroboration_summary(
    segment_text,
    articles
):
    """
    Convenience wrapper.

    Returns:
        {
            "count": int,
            "sources": [...]
        }
    """

    supporting_sources = (
        find_supporting_sources(
            segment_text,
            articles
        )
    )

    return {
        "count": len(
            supporting_sources
        ),
        "sources": supporting_sources
    }


# =====================================
# TEST
# =====================================

if __name__ == "__main__":

    test_articles = [

        {
            "source": "NIH",

            "title":
                "Sleep Quality Linked To Dementia Risk",

            "summary":
                "Researchers found poor sleep patterns increase dementia risk.",

            "url":
                "https://example.com/nih"
        },

        {
            "source": "NASA",

            "title":
                "New Artemis Mission Update",

            "summary":
                "Moon mission preparations continue.",

            "url":
                "https://example.com/nasa"
        }
    ]

    results = find_supporting_sources(
        "Poor sleep may increase dementia risk.",
        test_articles
    )

    print(
        "\nMatches Found:",
        len(results)
    )

    for result in results:

        print(
            f"{result.source} "
            f"{result.score}"
        )