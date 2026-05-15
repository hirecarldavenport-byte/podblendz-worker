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
from podpal.audio.tts import generate_audio  # ✅ Azure TTS

from podpal.ai.pipeline import process_clusters
from podpal.boards.board_config import BOARD_CONFIG

router = APIRouter()


# ---------------- CLEAN TEXT ----------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------- LANGUAGE FILTER ----------------
def is_english_text(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except:
        return False


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


# ---------------- STRICT DOMAIN FILTER (FIXED) ----------------
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    required_terms = [
        "gene", "dna", "genome", "genetic",
        "crispr", "sequencing", "genomics"
    ]

    strict_terms = ["biology", "molecular", "cell", "research"]

    bad_terms = [
        "author", "book", "biography", "devotional",
        "mindset", "faith", "scripture",
        "lifestyle", "journey", "motivation"
    ]

    if len(text.split()) < 20:
        return False

    if any(b in text for b in bad_terms):
        return False

    if not any(r in text for r in required_terms):
        return False

    if not any(s in text for s in strict_terms):
        return False

    return True


# ---------------- THEME EXTRACTION ----------------
def extract_theme(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\[.*?\]", "", text)

    keywords = [
        "gene", "dna", "genome",
        "crispr", "sequencing",
        "molecular", "biology"
    ]

    hits = [k for k in keywords if k in text]

    return " ".join(hits[:5])


# ---------------- MATCH SCORING ----------------
def match_episode_to_theme(ep, theme: str) -> int:
    text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

    words = [w for w in theme.split() if len(w) > 3]

    return sum(1 for w in words if w in text)


# ---------------- CORE FUNCTION ----------------
def run_blend(query: str, target_minutes: int):

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    print(f"\n QUERY: {query}")

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

    # -------- FILTER (UPGRADED) --------
    filtered = []

    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

        # ✅ language filter
        if not is_english_text(text):
            continue

        if is_good_domain_text(text):
            filtered.append(ep)

    if not filtered:
        print("⚠️ fallback to minimal safe set")
        filtered = blended[:3]

    blended = filtered[:4]

    print(f"✅ Using {len(blended)} episodes")

    # -------- BUILD SEGMENTS --------
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

    clustered = process_clusters(cluster_input)

    themes = []
    for c in clustered:
        narration = c.get("narration", "")
        theme = extract_theme(narration)
        if len(theme.split()) >= 2:
            themes.append(theme)

    if not themes:
        themes = [
            "genome sequencing",
            "gene editing crispr",
            "molecular biology dna"
        ]

    print(f" Themes: {themes}")

    # -------- AUDIO URL SELECTION --------
    ordered_audio_urls = []

    for ep in blended:
        audio_url = next(
            (l.get("href") for l in ep.get("links", [])
             if "audio" in l.get("type", "")),
            None
        )
        if audio_url:
            ordered_audio_urls.append(audio_url)

    # -------- DOWNLOAD --------
    clip_paths = []

    for url in ordered_audio_urls:
        try:
            fn = download_episode_audio(url)
            if fn:
                clip_paths.append(str(RAW_DIR / fn))
        except:
            continue

    print(f"🎧 Clips collected: {len(clip_paths)}")

    # -------- INTRO TEXT --------
    intro_text = f"This blend explores {query}. "

    if titles:
        intro_text += "Featuring: " + ", ".join(titles[:2]) + ". "

    if themes:
        intro_text += "Key topics include: " + ", ".join(themes[:2]) + "."

    
    print(f" Intro: {intro_text}")

    # -------- BUILD FINAL AUDIO --------
    final_sequence = []

    try:
        intro_audio = generate_audio(intro_text, filename_prefix="intro")
        final_sequence.append(intro_audio)
        print("✅ Intro audio added")
    except Exception as e:
        print(f"⚠️ Intro failed: {e}")

    for i, clip in enumerate(clip_paths):

        if i > 0 and i < len(themes):
            try:
                t_audio = generate_audio(
                    f"Next, we explore {themes[i]}.",
                    filename_prefix="transition"
                )
                final_sequence.append(t_audio)
                print(f"✅ Transition {i}")
            except:
                pass

        final_sequence.append(clip)

    # -------- STITCH --------
    final_audio = None

    if final_sequence:
        try:
            fn = stitch_blendz(final_sequence, target_minutes)
            final_audio = f"/audio/final/{fn}"
        except Exception as e:
            print("🔥 stitch error:", e)

    return {
        "query": query,
        "themes": themes,
        "results": blended,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
        "intro_text": intro_text,
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






