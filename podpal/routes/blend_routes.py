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
from podpal.audio.tts import generate_audio  # ✅ ADDED (Azure TTS)

from podpal.ai.pipeline import process_clusters
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

# ---------------- STRICT DOMAIN FILTER ----------------
def is_good_domain_text(text: str) -> bool:
    text = text.lower()

    required_terms = ["gene", "dna", "genome", "genetic", "crispr"]
    domain_terms = ["sequencing", "biology", "molecular", "cell"]

    bad_context_terms = [
        "author", "book", "biography",
        "interview", "guest", "story",
        "life of", "history of"
    ]

    if len(text.split()) < 20:
        return False

    if any(b in text for b in bad_context_terms):
        return False

    if not any(r in text for r in required_terms):
        return False

    score = sum(1 for d in domain_terms if d in text)

    return score >= 1

# ---------------- CLEAN / EXTRACT TRUE THEMES ----------------
def extract_theme(text: str) -> str:
    text = text.lower()

    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(
        r"(welcome to.*?|in this episode.*?|today we.*?|join us.*?)[,\.]",
        "",
        text
    )

    keywords = [
        "gene", "dna", "genome", "genetic",
        "crispr", "sequencing", "mutation",
        "biotech", "molecular", "cell"
    ]

    hits = [k for k in keywords if k in text]

    return " ".join(hits[:6])

# ---------------- SMART MATCH SCORING ----------------
def match_episode_to_theme(ep, theme: str) -> int:
    text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()

    stopwords = {"the", "is", "and", "to", "of", "in", "we", "this"}
    words = [w for w in theme.split() if w not in stopwords and len(w) > 3]

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

    # -------- FILTER --------
    filtered = []
    for ep in blended:
        text = (ep.get("title", "") + " " + ep.get("summary", "")).lower()
        if is_good_domain_text(text):
            filtered.append(ep)

    if not filtered:
        print("⚠️ fallback to minimal safe set")
        filtered = blended[:3]

    blended = filtered[:4]
    print(f"✅ Using {len(blended)} episodes")

    # -------------------------------------------------
    # ✅ BUILD SEGMENTS (FOR AI)
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
    # ✅ AI CLUSTERING
    # -------------------------------------------------
    clustered = process_clusters(cluster_input)

    themes = []
    for c in clustered:
        narration = c.get("narration", "")
        if narration:
            theme = extract_theme(narration)
            if len(theme.split()) >= 2:
                themes.append(theme)

    if len(themes) == 0:
        print("⚠️ AI theme failure → fallback")
        themes = [
            "genome sequencing",
            "gene editing crispr",
            "molecular biology dna"
        ]

    print(f" Themes: {themes}")

    # -------------------------------------------------
    # ✅ ORDER EPISODES (DIVERSE)
    # -------------------------------------------------
    ordered_audio_urls = []
    used_titles = set()

    for theme in themes:

        scored = []

        for ep in blended:

            if ep.get("title") in used_titles:
                continue

            score = match_episode_to_theme(ep, theme)

            if score > 0:
                scored.append((score, ep))

        scored.sort(reverse=True, key=lambda x: x[0])

        if scored:
            best_ep = scored[0][1]
            used_titles.add(best_ep.get("title"))

            audio_url = next(
                (l.get("href") for l in best_ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None
            )

            if audio_url:
                ordered_audio_urls.append(audio_url)

    if len(ordered_audio_urls) < 2:
        print("⚠️ expanding clips")

        for ep in blended:
            audio_url = next(
                (l.get("href") for l in ep.get("links", [])
                 if "audio" in l.get("type", "")),
                None
            )
            if audio_url:
                ordered_audio_urls.append(audio_url)

    # -------------------------------------------------
    # ✅ DOWNLOAD
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
    # ✅ INTRO SUMMARY
    # -------------------------------------------------
    intro_text = f"This blend explores {query}. "

    if titles:
        intro_text += "Featuring: " + ", ".join(titles[:3]) + ". "

    if themes:
        intro_text += "Key topics include: " + ", ".join(themes[:3]) + "."

    print(f" Intro: {intro_text}")

    # -------------------------------------------------
    # ✅ NEW: BUILD FINAL AUDIO SEQUENCE
    # -------------------------------------------------
    final_sequence = []

    try:
        intro_audio = generate_audio(intro_text, filename_prefix="intro")
        final_sequence.append(intro_audio)
        print("✅ Intro audio added")
    except Exception as e:
        print(f"⚠️ Intro TTS failed: {e}")

    enhanced_sequence = []

    for i, clip in enumerate(clip_paths):

        if i > 0 and i < len(themes):
            transition_text = f"Building on that, we now explore {themes[i]}."

            try:
                t_audio = generate_audio(
                    transition_text,
                    filename_prefix="transition"
                )
                enhanced_sequence.append(t_audio)
                print(f"✅ Transition {i} added")
            except Exception as e:
                print(f"⚠️ Transition failed: {e}")

        enhanced_sequence.append(clip)

    final_sequence = final_sequence + enhanced_sequence

    # -------------------------------------------------
    # ✅ STITCH (UPDATED INPUT)
    # -------------------------------------------------
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






