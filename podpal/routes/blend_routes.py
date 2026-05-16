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

from podpal.ai.pipeline import process_clusters
from podpal.boards.board_config import BOARD_CONFIG

router = APIRouter()


# ===============================
# ✅ FALLBACK SOURCES (STABILITY LAYER)
# ===============================
FALLBACK_AUDIO_SOURCES = {
    "genetics": [
        "https://sphinx.acast.com/p/open/s/65736d39d32e730012c98919/e/69fcce54051b78474edb8b8e/media.mp3",
        "https://anchor.fm/s/fb43d2d4/podcast/play/92030581/https://d3ctxlq1ktw2nl.cloudfront.net/staging/2024-8-22/386803392-44100-2-8e5eb4d5876af.m4a",
        "https://sphinx.acast.com/p/open/s/657b178ababc4c0017c46b78/e/69e6893923929c3a2a3525e0/media.mp3",
    ]
}


# ===============================
# ✅ TEXT CLEAN / SAFE TTS
# ===============================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def sanitize_tts_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_english_text(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except:
        return False


# ===============================
# ✅ FILTER (STRONG BUT NOT OVERLY STRICT)
# ===============================
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    required_terms = [
        "gene", "dna", "genome", "genetic",
        "crispr", "sequencing", "genomics"
    ]

    bad_terms = [
        "story", "life", "family",
        "crime", "relationship",
        "celebrity", "tv", "drama"
    ]

    if any(b in text for b in bad_terms):
        return False

    return any(r in text for r in required_terms)


# ===============================
# ✅ CORE BLEND FUNCTION
# ===============================
def run_blend(query: str, target_minutes: int):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n QUERY: {query}")

    # -------- SEARCH --------
    feed_urls = []
    for q in [query]:
        try:
            feed_urls.extend(resolve_search_term(q))
        except:
            continue

    feed_urls = list(set(feed_urls))[:20]

    # -------- FETCH --------
    episodes_by_feed = {}
    for url in feed_urls:
        try:
            resolved = resolve_podcast_source(url)
            rss = fetch_rss_feed(resolved.feed_url)
            episodes_by_feed[resolved.feed_url] = rss.get("items", [])
        except:
            continue

    blended = round_robin_blend(episodes_by_feed, 1, 6)

    # -------- FILTER --------
    filtered = []
    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

        if not is_english_text(text):
            continue

        if is_good_domain_text(text):
            filtered.append(ep)

    if len(filtered) < 3:
        print("⚠️ Expanding pool")
        filtered = blended[:5]

    blended = filtered[:5]

    print(f"✅ Using {len(blended)} episodes")

    # -------- AUDIO URL SELECTION --------
    ordered_audio_urls = []
    seen = set()

    for ep in blended:
        audio_url = next(
            (l.get("href") for l in ep.get("links", [])
             if "audio" in l.get("type", "")),
            None
        )

        if audio_url and audio_url not in seen:
            ordered_audio_urls.append(audio_url)
            seen.add(audio_url)

    # -------- DOWNLOAD (FIXED) --------
    clip_paths = []

    for url in ordered_audio_urls:
        try:
            fn = download_episode_audio(url)

            if fn:  # ✅ critical fix
                clip_paths.append(str(RAW_DIR / fn))
            else:
                print(f"⚠️ download failed: {url}")

        except Exception as e:
            print(f"⚠️ error downloading {url}: {e}")

    # -------- FALLBACK --------
    if len(clip_paths) < 3:
        print("⚠️ Using fallback pool")

        fallback_urls = FALLBACK_AUDIO_SOURCES.get("genetics", [])

        for url in fallback_urls:
            try:
                fn = download_episode_audio(url)

                if fn:
                    clip_paths.append(str(RAW_DIR / fn))
                else:
                    print(f"⚠️ fallback failed: {url}")

            except Exception as e:
                print(f"⚠️ fallback error: {url} → {e}")

            if len(clip_paths) >= 3:
                break

    print(f"🎧 Clips collected: {len(clip_paths)}")

    # -------- THEMES --------
    themes = [
        "genome sequencing",
        "gene editing",
        "molecular biology"
    ]

    # -------- INTRO --------
    intro_text = sanitize_tts_text(
        f"Welcome to PodBlendz. This episode explores {query}. "
        f"We begin with {themes[0]}."
    )

    # -------- BUILD SEQUENCE --------
    final_sequence = []

    try:
        intro_audio = generate_audio(intro_text, "intro")
        final_sequence.append(intro_audio)
        print("✅ Intro added")
    except Exception as e:
        print(f"⚠️ Intro failed: {e}")

    clip_index = 0

    for i, theme in enumerate(themes):

        narration_text = sanitize_tts_text(
            f"Building on that, we now explore {theme}."
            if i > 0 else f"We begin with {theme}."
        )

        try:
            narration_audio = generate_audio(narration_text, "transition")
            final_sequence.append(narration_audio)
        except Exception as e:
            print(f"⚠️ transition failed: {e}")

        if clip_index < len(clip_paths):
            final_sequence.append(clip_paths[clip_index])
            clip_index += 1

    # -------- STITCH --------
    final_audio = None

    try:
        fn = stitch_blendz(final_sequence, target_minutes)
        final_audio = f"/audio/final/{fn}"
    except Exception as e:
        print("🔥 stitch error:", e)

    return {
        "query": query,
        "clip_count": len(clip_paths),
        "final_audio": final_audio
    }


# ===============================
# ✅ ENDPOINT
# ===============================
@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board = BOARD_CONFIG.get(board_id.lower())

    if not board:
        return {"error": "Board not found"}

    return run_blend(board["query"], minutes or 5)





