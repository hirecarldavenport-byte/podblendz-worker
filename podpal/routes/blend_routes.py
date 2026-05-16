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
from podpal.audio.tts import generate_audio

from podpal.boards.board_config import BOARD_CONFIG

router = APIRouter()


# ✅ FALLBACK SOURCES
FALLBACK_AUDIO_SOURCES = {
    "genetics": [
        "https://sphinx.acast.com/p/open/s/65736d39d32e730012c98919/e/69fcce54051b78474edb8b8e/media.mp3",
        "https://anchor.fm/s/fb43d2d4/podcast/play/92030581/https://d3ctxlq1ktw2nl.cloudfront.net/staging/2024-8-22/386803392-44100-2-8e5eb4d5876af.m4a",
        "https://sphinx.acast.com/p/open/s/657b178ababc4c0017c46b78/e/69e6893923929c3a2a3525e0/media.mp3",
    ]
}


# ✅ HARD-SAFE TTS (FINAL FIX)
def sanitize_tts_text(text: str) -> str:
    if not text:
        return "This episode explores the topic."

    text = text.replace("\n", " ")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9 .,!?-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 300:
        text = text[:300].rsplit(" ", 1)[0]

    if not text:
        return "Continuing the discussion."

    return text


def safe_generate_audio(text: str, label: str):
    try:
        clean = sanitize_tts_text(text)
        return generate_audio(clean, label)
    except Exception as e:
        print(f"⚠️ TTS failed ({label}): {e}")
        try:
            return generate_audio("Continuing the conversation.", label)
        except Exception:
            print("🔥 TTS failed completely")
            return None


# ✅ FILTER
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    required = ["gene", "dna", "genome", "crispr", "sequencing"]
    bad = ["story", "life", "crime", "relationship", "tv"]

    if any(b in text for b in bad):
        return False

    return any(r in text for r in required)


# ✅ COHERENCE ENGINE
def is_cohesive_cluster(texts: List[str]) -> bool:
    keywords = ["gene", "dna", "genome", "crispr", "sequencing"]

    strong = 0

    for t in texts:
        score = sum(1 for k in keywords if k in t.lower())
        if score >= 2:
            strong += 1

    return strong >= 3


# ✅ MAIN FUNCTION
def run_blend(query: str, target_minutes: int):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n QUERY: {query}")

    # -------- SEARCH --------
    feed_urls = []
    try:
        feed_urls = resolve_search_term(query)
    except:
        pass

    feeds = []
    for url in list(set(feed_urls))[:20]:
        try:
            feeds.append(resolve_podcast_source(url))
        except:
            continue

    episodes = {}
    for f in feeds:
        try:
            rss = fetch_rss_feed(f.feed_url)
            episodes[f.feed_url] = rss.get("items", [])
        except:
            continue

    blended = round_robin_blend(episodes, 1, 6)

    # -------- FILTER --------
    filtered = []
    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

        if is_good_domain_text(text):
            filtered.append(ep)

    if len(filtered) < 3:
        print("⚠️ expanding pool")
        filtered = blended[:5]

    blended = filtered[:5]

    # -------- COHERENCE --------
    segment_texts = [
        (ep.get("title", "") + " " + ep.get("summary", "")).lower()
        for ep in blended
    ]

    is_cohesive = is_cohesive_cluster(segment_texts)

    print(f"🧠 Cohesion: {is_cohesive}")

    # -------- AUDIO --------
    clip_paths = []
    seen = set()

    for ep in blended:
        audio_url = next(
            (l.get("href") for l in ep.get("links", [])
             if "audio" in l.get("type", "")),
            None
        )

        if audio_url and audio_url not in seen:
            fn = download_episode_audio(audio_url)

            if fn:
                clip_paths.append(str(RAW_DIR / fn))
                seen.add(audio_url)
            else:
                print(f"⚠️ download failed: {audio_url}")

    # -------- FALLBACK --------
    if len(clip_paths) < 3:
        print("⚠️ using fallback")

        for url in FALLBACK_AUDIO_SOURCES["genetics"]:
            fn = download_episode_audio(url)

            if fn:
                clip_paths.append(str(RAW_DIR / fn))

            if len(clip_paths) >= 3:
                break

    print(f"🎧 Clips: {len(clip_paths)}")

    # -------- BUILD SEQUENCE --------
    final_sequence = []

    if is_cohesive:
        print("✅ MULTI MODE")

        intro = f"Welcome to PodBlendz. This episode explores {query} from multiple perspectives."

        intro_audio = safe_generate_audio(intro, "intro")
        if intro_audio:
            final_sequence.append(intro_audio)

        for i, clip in enumerate(clip_paths[:3]):

            narration = (
                "We begin with a foundational idea."
                if i == 0 else
                "Building on that, we continue exploring this concept."
            )

            n_audio = safe_generate_audio(narration, "transition")
            if n_audio:
                final_sequence.append(n_audio)

            final_sequence.append(clip)

    else:
        print("✅ SINGLE MODE")

        clip = clip_paths[0]

        intro_audio = safe_generate_audio(
            f"Welcome to PodBlendz. This episode focuses on {query}.",
            "intro"
        )

        if intro_audio:
            final_sequence.append(intro_audio)

        for _ in range(3):

            n_audio = safe_generate_audio(
                "We continue unpacking this idea.",
                "transition"
            )

            if n_audio:
                final_sequence.append(n_audio)

            final_sequence.append(clip)

    # -------- STITCH --------
    final_audio = None

    try:
        fn = stitch_blendz(final_sequence, target_minutes)
        final_audio = f"/audio/final/{fn}"
    except Exception as e:
        print("🔥 stitch error:", e)

    return {
        "query": query,
        "mode": "multi" if is_cohesive else "single",
        "clip_count": len(clip_paths),
        "final_audio": final_audio
    }


# ✅ ENDPOINT
@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board = BOARD_CONFIG.get(board_id.lower())

    if not board:
        return {"error": "Board not found"}

    return run_blend(board["query"], minutes or 5)





