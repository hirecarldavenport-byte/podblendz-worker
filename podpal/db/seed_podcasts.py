"""
Seed Podcasts into Database

Creates initial Podcast records from master registry
"""

from podpal.topics.master_topic_podcasters import TOP_PODCASTERS_BY_MASTER_TOPIC
from podpal.db.session import get_session
from podpal.db.models import Podcast


def seed_podcasts():
    session = get_session()
    created = 0

    for topic, podcasters in TOP_PODCASTERS_BY_MASTER_TOPIC.items():
        for podcaster in podcasters:

            feed_url = podcaster.get("feed_url")
            if not feed_url:
                continue

            existing = session.query(Podcast).filter_by(id=podcaster["id"]).first()

            if existing:
                continue

            new_podcast = Podcast(
                id=podcaster["id"],
                name=podcaster["name"],
                feed_url=feed_url,
            )

            session.add(new_podcast)
            created += 1

    session.commit()
    print(f"✅ Seeded {created} podcasts into database")


if __name__ == "__main__":
    seed_podcasts()
