# podpal/intelligence/test_confidence.py

from podpal.intelligence.rss_ingest import (
    fetch_articles
)

from podpal.intelligence.corroboration import (
    find_supporting_sources
)

from podpal.intelligence.confidence import (
    calculate_confidence
)

articles = fetch_articles()

query = """
Artificial intelligence is changing jobs
and workforce productivity.
"""

sources = find_supporting_sources(
    query,
    articles
)

confidence = calculate_confidence(
    sources
)

print("\nCONFIDENCE")
print(confidence)

print("\nTOP SOURCES")

for source in confidence.sources[:10]:

    print(
        source.source,
        source.score,
        source.title
    )