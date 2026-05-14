from fastapi import APIRouter
from typing import List, Optional
import re
from pathlib import Path

from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed
from podpal.blending.round_robin import round_robin_blend

from podpal.audio.ingest import download_episode_audio
from podpal.audio.stitch import stitch_blendz

from podpal.boards.board_config import BOARD_CONFIG

router = APIRouter()


# ---------------- CLEAN TEXT ----------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------- SEARCH QUERIES ----------------
def get_queries(query: str) -> List[str]:
    q = query.lower()

    if "genetics" in q:
        return [
            "gene editing crispr dna podcast",
            "genomics biotechnology podcast",
            "molecular biology genetics podcast",
        ]

    return [query]


# ---------------- DOMAIN FILTER ----------------
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    good_terms = [
        "gene", "dna", "genome", "genetic",
        "crispr", "biology", "biotech",
        "molecular", "cell", "mutation",
        "sequencing", "antibody"
    ]

    bad_terms = [
        "mindset", "relationship", "fitness",
        "spiritual", "self help", "finance",
        "economy", "oil", "opec"
    ]

    if any(b in text for b in bad_terms):
        return False

    hits = sum(1 for g in good_terms if g in text)

    return hits >= 2


# ---------------- CORE FUNCTION ----------------
def run_blend(query: str, target_minutes: int):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n🔍 QUERY: {query}")

    # -------- SEARCH --------
    feed_urls = []
    for q in get_queries(query):
        try:
            feed_urls.extend(resolve_search_term(q))
        except:
            continue

    feed_urls = list(set(feed_urls))[:30]

    # -------- RESOLVE --------
    feeds = []
    for url in feed_urls:
        try:
            f = resolve_podcast_source(url)
            if f:
                feeds.append(f)
        except:
            continue

    # -------- FETCH --------
    episodes_by_feed = {}
    for f in feeds:
        try:
            rss = fetch_rss_feed(f.feed_url)
            episodes_by_feed[f.feed_url] = rss.get("items", [])
        except:
            episodes_by_feed[f.feed_url] = []

    blended = round_robin_blend(episodes_by_feed, 1, 6)

    # -------- FILTER --------
    filtered = []
    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

        if is_good_domain_text(text) and len(text.split()) > 20:
            filtered.append(ep)

    if not filtered:
        print("⚠️ fallback to unfiltered")
        filtered = blended[:4]

    blended = filtered[:4]
    print(f"✅ Using {len(blended)} episodes")

    # -------- DOWNLOAD AUDIO --------
    clip_paths = []

    for ep in blended:
        try:
            audio_url = next(
                (l.get("href") for l in ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None
            )

            if audio_url:
                fn = download_episode_audio(audio_url)
                if fn:
                    clip_paths.append(str(RAW_DIR / fn))

        except:
            continue

    if len(clip_paths) == 0:
        print("❌ No audio clips found")

    print(f"🎧 Clips collected: {len(clip_paths)}")

    # -------- STITCH --------
    final_audio = None

    if clip_paths:
        try:
            fn = stitch_blendz(clip_paths, target_minutes)
            final_audio = f"/audio/final/{fn}"
        except Exception as e:
            print("🔥 Stitch error:", e)

    return {
        "query": query,
        "results": blended,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
    }


# ---------------- ENDPOINT ----------------
@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board = BOARD_CONFIG.get(board_id)

    if not board:
        return {"error": "Board not found"}

    return {
        "mode": "board",
        **run_blend(
            board["query"],
            minutes or board["default_minutes"],
        ),
    }





