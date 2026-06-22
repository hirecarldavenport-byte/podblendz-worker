"""
podpal/intelligence/rss_ingest.py

Trusted external sources used to corroborate
podcast segments and generate confidence scores.
"""

RSS_FEEDS = {

    # =====================================
    # HEALTH & MEDICINE
    # =====================================

    "NIH Research Matters":
        "https://www.nih.gov/feed/rss.xml",

    "CDC Newsroom":
        "https://tools.cdc.gov/api/v2/resources/media/132608.rss",

    "MedlinePlus Health News":
        "https://medlineplus.gov/feeds/news_en.xml",

    # =====================================
    # SCIENCE
    # =====================================

    "ScienceDaily":
        "https://www.sciencedaily.com/rss/all.xml",

    "Nature":
        "https://www.nature.com/nature.rss",

    "NASA News":
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",

    # =====================================
    # TECHNOLOGY & AI
    # =====================================

    "MIT News":
        "https://news.mit.edu/rss/feed",

    "MIT AI News":
        "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",

    "Ars Technica":
        "https://feeds.arstechnica.com/arstechnica/index",

    # =====================================
    # BUSINESS & ECONOMICS
    # =====================================

    "OECD":
        "https://www.oecd.org/newsroom/rss.xml",

    "World Bank":
        "https://blogs.worldbank.org/en/rss.xml",

    "IMF":
        "https://www.imf.org/en/News/RSS",

    # =====================================
    # EDUCATION
    # =====================================

    "Edutopia":
        "https://www.edutopia.org/rss.xml",

    # =====================================
    # ENVIRONMENT
    # =====================================

    "NASA Earth":
        "https://www.nasa.gov/rss/dyn/earth.rss",

    "NOAA":
        "https://www.noaa.gov/rss.xml",
}
import feedparser


def fetch_articles():

    articles = []

    for source_name, feed_url in RSS_FEEDS.items():

        try:

            feed = feedparser.parse(feed_url)

            for entry in feed.entries:

                articles.append(
                    {
                        "source": source_name,
                        "title": getattr(
                            entry,
                            "title",
                            ""
                        ),
                        "summary": getattr(
                            entry,
                            "summary",
                            ""
                        ),
                        "url": getattr(
                            entry,
                            "link",
                            ""
                        ),
                        "published": getattr(
                            entry,
                            "published",
                            ""
                        ),
                    }
                )

            print(
                f"✅ {source_name}: "
                f"{len(feed.entries)} articles"
            )

        except Exception as e:

            print(
                f"❌ {source_name}: {e}"
            )

    return articles
if __name__ == "__main__":

    articles = fetch_articles()

    print(
        f"\n📚 Total Articles: "
        f"{len(articles)}"
    )

    if articles:
        print("\nSample:")
        print(articles[0])

        if __name__ == "__main__":

         articles = fetch_articles()

    print(f"\nArticles: {len(articles)}")

    if articles:

        print("\nSample Article:\n")

        print(articles[0])