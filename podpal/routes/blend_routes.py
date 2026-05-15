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

from podpal.ai.pipeline import process_clusters  # ✅ NEW

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

    if len(text.split()) < 20:
        return False

    return any(g in text for g in good_terms)


# ---------------- MATCH SCORING ----------------
def match_episode_to_theme(ep, theme: str) -> int:
    text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()
    words = theme.split()
    return sum(1 for w in words if w in text)


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

        if is_good_domain_text(text):
            filtered.append(ep)

    if not filtered:
        print("⚠️ fallback")
        filtered = blended[:4]

    blended = filtered[:4]
    print(f"✅ Using {len(blended)} episodes")

    # -------------------------------------------------
    # ✅ STEP 1: BUILD SEGMENTS
    # -------------------------------------------------
    segments = []
    titles = []

    for ep in blended:
        title = ep.get("title", "")
        summary = clean_text(ep.get("summary", ""))

        if summary:
            segments.append(f"{title}. {summary[:400]}")
            titles.append(title)

    cluster_input = [
        {"id": i + 1, "segments": [s]}
        for i, s in enumerate(segments)
    ]

    # -------------------------------------------------
    # ✅ STEP 2: CLUSTER THEMES
    # -------------------------------------------------
    clustered = process_clusters(cluster_input)

    themes = []
    for c in clustered:
        narration = c.get("narration", "")
        if narration:
            themes.append(narration.lower())

    print(f"🧠 Themes detected: {len(themes)}")

    # -------------------------------------------------
    # ✅ STEP 3: ORDER EPISODES BY THEMES
    # -------------------------------------------------
    ordered_audio_urls = []

    for theme in themes:

        scored = []

        for ep in blended:
            score = match_episode_to_theme(ep, theme)
            if score > 0:
                scored.append((score, ep))

        scored.sort(reverse=True, key=lambda x: x[0])

        if scored:
            best_ep = scored[0][1]

            audio_url = next(
                (l.get("href") for l in best_ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None
            )

            if audio_url:
                ordered_audio_urls.append(audio_url)

    # fallback
    if not ordered_audio_urls:
        print("⚠️ fallback ordering")

        for ep in blended:
            audio_url = next(
                (l.get("href") for l in ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None
            )
            if audio_url:
                ordered_audio_urls.append(audio_url)

    # -------------------------------------------------
    # ✅ STEP 4: DOWNLOAD IN ORDER
    # -------------------------------------------------
    clip_paths = []

    for url in ordered_audio_urls:
        try:
            fn = download_episode_audio(url)
            if fn:
                clip_paths.append(str(RAW_DIR / fn))
        except:
            continue

    print(f"🎧 Clips collected: {len(clip_paths)}")

    # -------------------------------------------------
    # ✅ STEP 5: BUILD SUMMARY OPENING TEXT
    # -------------------------------------------------
    intro_text = f"This blend explores {query}. Featuring insights from: "

    intro_text += ", ".join(titles[:3]) + "."

    print(f"🎤 Intro: {intro_text}")

    # (we'll convert this to TTS later)

    # -------------------------------------------------
    # ✅ STITCH
    # -------------------------------------------------
    final_audio = None

    if clip_paths:
        try:
            fn = stitch_blendz(clip_paths, target_minutes)
            final_audio = f"/audio/final/{fn}"
        except Exception as e:
            print("🔥 stitch error:", e)

    return {
        "query": query,
        "themes": themes,  # ✅ NEW (debug visibility)
        "results": blended,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
        "intro_text": intro_text,  # ✅ ready for narration
    }


# ---------------- ENDPOINT ----------------
@router.get("/board/{board_id}")
def get_board(board_id: str, minutes: Optional[int] = None):

    board_id = board_id.lower()

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





