import hashlib
import hmac
import time
import requests
import os

from dotenv import load_dotenv

# ✅ Load env
load_dotenv()


BASE_URL = "https://api.podcastindex.org/api/1.0"


# -------------------------------------------------
# Get credentials SAFELY (no crash at import time)
# -------------------------------------------------

def _get_credentials():
    api_key = os.getenv("PODCASTINDEX_API_KEY")
    api_secret = os.getenv("PODCASTINDEX_API_SECRET")

    if not api_key or not api_secret:
        raise RuntimeError(
            "PodcastIndex API credentials are not set. "
            "Please set PODCASTINDEX_API_KEY and PODCASTINDEX_API_SECRET."
        )

    return api_key, api_secret


# -------------------------------------------------
# PodcastIndex authentication headers
# -------------------------------------------------

def _auth_headers() -> dict:
    api_key, api_secret = _get_credentials()

    epoch = str(int(time.time()))

    auth_string = api_key + api_secret + epoch
    digest = hashlib.sha1(auth_string.encode("utf-8")).hexdigest()

    return {
        "X-Auth-Date": epoch,
        "X-Auth-Key": api_key,
        "Authorization": digest,
        "User-Agent": "PodBlendz/1.0",
    }


# -------------------------------------------------
# PodcastIndex search wrapper
# -------------------------------------------------

def search_podcasts(query: str, limit: int = 20) -> list:
    """
    Search PodcastIndex by term and return RSS feed URLs.
    """
    url = f"{BASE_URL}/search/byterm"

    params = {
        "q": query,
        "max": limit,
        "clean": True,
    }

    response = requests.get(
        url,
        headers=_auth_headers(),
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()
    feeds = data.get("feeds", [])

    return [
        f["url"] for f in feeds
        if isinstance(f, dict) and "url" in f
    ]


def search_podcasts_by_title(query: str, limit: int = 10) -> list:
    """
    Search PodcastIndex by podcast TITLE only.
    """
    url = f"{BASE_URL}/search/bytitle"

    params = {
        "q": query,
        "max": limit,
        "clean": True,
    }

    response = requests.get(
        url,
        headers=_auth_headers(),
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()
    feeds = data.get("feeds", [])

    return [
        f["url"] for f in feeds
        if isinstance(f, dict) and "url" in f
    ]