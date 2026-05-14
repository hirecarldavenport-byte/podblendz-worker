from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed
from podpal.blending.round_robin import round_robin_blend

from podpal.ai.pipeline import process_clusters

from podpal.audio.ingest import download_episode_audio
from podpal.audio.tts import generate_audio
from podpal.audio.stitch import stitch_blendz

from podpal.boards.board_config import BOARD_CONFIG

router = APIRouter()

# -------------------------------------------------
# ✅ CLEAN TEXT
# -------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    return re.sub(r"\s+", " ", text).strip()


# -------------------------------------------------
# ✅ SPLIT INTO CHUNKS
# -------------------------------------------------
def split_into_chunks(text: str, max_len: int = 300):
    sentences = text.split(". ")
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < max_len:
            current += s + ". "
        else:
            chunks.append(current.strip())
            current = s + ". "
    if current:
        chunks.append(current.strip())
    return chunks


# -------------------------------------------------
# ✅ MULTI QUERY
# -------------------------------------------------
def get_queries(query: str) -> List[str]:
    q = query.lower()

    if "genetics" in q:
        return [
            "crispr gene editing dna podcast",
            "genomics molecular biology podcast",
            "biotech genetics research podcast",
        ]

    return [query]


# -------------------------------------------------
# ✅ BALANCED DOMAIN FILTER (FIXED)
# -------------------------------------------------
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    strong = ["gene", "dna", "genetic", "genome", "genomics"]
    medium = [
        "crispr", "biology", "biotech",
        "mutation", "cell", "antibody",
        "molecular", "sequencing", "therapy"
    ]

    bad = ["mindset", "spiritual", "relationship", "pelvic", "fitness"]

    if any(b in text for b in bad):
        return False

    strong_hits = sum(1 for w in strong if w in text)
    medium_hits = sum(1 for w in medium if w in text)

    if strong_hits >= 1 and medium_hits >= 1:
        return True

    if medium_hits >= 2:
        return True

    return False


# -------------------------------------------------
# ✅ CLEAN FOR TTS
# -------------------------------------------------
def clean_for_tts(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"http\S+", "", text)

    text = text.encode("ascii", "ignore").decode()

    text = re.sub(r"[^a-zA-Z0-9.,!?;:'\"()\-\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


# -------------------------------------------------
# ✅ FINAL TTS VALIDATION (CRITICAL)
# -------------------------------------------------
def is_valid_tts_input(text: str) -> bool:
    if not text:
        return False
    if len(text) < 60:
        return False
    if not re.search(r"[a-zA-Z]", text):
        return False

    bad_patterns = ["please provide", "subscribe", "visit", "http", "www"]
    if any(b in text.lower() for b in bad_patterns):
        return False

    return True


# -------------------------------------------------
# ✅ CORE BLEND FUNCTION
# -------------------------------------------------
def run_blend(query: str, target_minutes: int, enable_ai: bool):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n🔍 QUERY: {query}")

    # ---------------- SEARCH ----------------
    feed_urls = []
    for q in get_queries(query):
        try:
            feed_urls.extend(resolve_search_term(q))
        except:
            continue

    feed_urls = list(set(feed_urls))[:25]

    feeds = []
    for url in feed_urls:
        try:
            f = resolve_podcast_source(url)
            if f:
                feeds.append(f)
        except:
            continue

    episodes_by_feed = {}
    for f in feeds:
        try:
            rss = fetch_rss_feed(f.feed_url)
            episodes_by_feed[f.feed_url] = rss.get("items", [])
        except:
            episodes_by_feed[f.feed_url] = []

    blended = round_robin_blend(episodes_by_feed, 1, 6)

    # ---------------- FILTER ----------------
    filtered = []
    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

        if is_good_domain_text(text) and len(text.split()) > 25:
            filtered.append(ep)

    # ✅ fallback if filter too strict
    if not filtered:
        print("⚠️ No filtered matches — using fallback")
        filtered = blended[:3]

    blended = filtered[:3]
    print(f"✅ Using {len(blended)} episodes")

    # ---------------- AUDIO DOWNLOAD ----------------
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

    # ---------------- AI ----------------
    narration_paths = []
    ai_output = None

    if enable_ai:
        try:
            segments = []

            for ep in blended:
                raw = ep.get("summary") or ep.get("description")
                cleaned = clean_text(raw)

                if cleaned:
                    segments.extend(split_into_chunks(cleaned)[:2])

            # dedupe
            seen = set()
            segments = [s for s in segments if not (s[:80] in seen or seen.add(s[:80]))]

            if segments:
                clusters = [{"id": i + 1, "segments": [s]} for i, s in enumerate(segments[:5])]
                ai_output = process_clusters(clusters)

                for c in ai_output:
                    narration = c.get("narration")
                    safe = clean_for_tts(narration)

                    if is_valid_tts_input(safe):
                        try:
                            narration_paths.append(generate_audio(safe[:600]))
                        except:
                            continue

        except Exception as e:
            print("⚠️ AI error:", e)

    # ---------------- STITCH ----------------
    final_audio = None

    # ✅ ALWAYS have something to stitch
    if narration_paths:
        sequence = []
        for i in range(len(narration_paths)):
            sequence.append(narration_paths[i])
            if i < len(clip_paths):
                sequence.append(clip_paths[i])
    else:
        sequence = clip_paths

    if sequence:
        try:
            fn = stitch_blendz(sequence, target_minutes)
            final_audio = f"/audio/final/{fn}"
        except Exception as e:
            print("🔥 Stitch error:", e)

    return {
        "query": query,
        "results": blended,
        "ai": ai_output,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
    }


# -------------------------------------------------
# ✅ ENDPOINTS
# -------------------------------------------------
@router.post("/blend")
def preview_blend(
    query: Optional[str] = Body(default=None),
    enable_ai: bool = Body(default=True),
    target_minutes: int = Body(default=5),
):
    if not query:
        return {"error": "Query required"}

    return {"mode": "subject", **run_blend(query, target_minutes, enable_ai)}


@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board = BOARD_CONFIG.get(board_id)

    if not board:
        return {
            "error": "Board not found",
            "available_boards": list(BOARD_CONFIG.keys())
        }

    return {
        "mode": "board",
        "board_id": board_id,
        "title": board["title"],
        **run_blend(board["query"], minutes or board["default_minutes"], True),
    }


