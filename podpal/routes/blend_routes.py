from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

from podpal.search.resolve import resolve_search_term
from podpal.rss.resolver import resolve_podcast_source
from podpal.services.rss_test import fetch_rss_feed
from podpal.blending.round_robin import round_robin_blend

# ✅ AI
from podpal.ai.pipeline import process_clusters

# ✅ Audio pipeline
from podpal.audio.ingest import download_episode_audio
from podpal.audio.tts import generate_audio
from podpal.audio.stitch import stitch_blendz

router = APIRouter()


# -------------------------------------------------
# ✅ Utility
# -------------------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_into_chunks(text: str, max_len: int = 300):
    sentences = text.split(". ")
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) < max_len:
            current += sentence + ". "
        else:
            chunks.append(current.strip())
            current = sentence + ". "

    if current:
        chunks.append(current.strip())

    return chunks


# -------------------------------------------------
# ✅ BLEND ENDPOINT
# -------------------------------------------------
@router.post("/blend")
def preview_blend(
    query: Optional[str] = Body(default=None),
    podcaster_feed: Optional[str] = Body(default=None),
    enable_ai: bool = Body(default=True),
) -> Dict[str, Any]:

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DIR = BASE_DIR / "audio" / "raw"

    # =================================================
    # ✅ PODCASTER MODE
    # =================================================
    if podcaster_feed:
        from podpal.retrieval.podcasters import fetch_podcaster_episodes

        episodes = fetch_podcaster_episodes(podcaster_feed)

        return {
            "mode": "podcaster",
            "results": episodes or [],
            "episode_count": len(episodes) if episodes else 0,
        }

    # =================================================
    # ✅ SUBJECT MODE
    # =================================================
    if not query:
        return {
            "mode": "subject",
            "guidance": "Provide a query.",
            "results": [],
        }

    print(f"\n🔍 QUERY: {query}")

    # -------------------------------------------------
    # 1. Resolve feeds
    # -------------------------------------------------
    feed_urls = resolve_search_term(query)

    feeds = []
    for url in feed_urls:
        try:
            feed = resolve_podcast_source(url)
            if feed:
                feeds.append(feed)
        except Exception as e:
            print(f"⚠️ Feed fail: {e}")

    feeds = feeds[:25]

    # -------------------------------------------------
    # 2. Fetch episodes
    # -------------------------------------------------
    episodes_by_feed: Dict[str, List[Any]] = {}

    for feed in feeds:
        try:
            rss = fetch_rss_feed(feed.feed_url)
            episodes_by_feed[feed.feed_url] = rss.get("items", []) if rss else []
        except Exception as e:
            print(f"⚠️ RSS fail: {e}")
            episodes_by_feed[feed.feed_url] = []

    # -------------------------------------------------
    # 3. Blend episodes
    # -------------------------------------------------
    blended_episodes = round_robin_blend(
        episodes_by_podcaster=episodes_by_feed,
        max_per_podcaster=1,
        max_total=3,
    )

    # -------------------------------------------------
    # 4. Download audio (EPISODE LEVEL)
    # -------------------------------------------------
    clip_paths: List[str] = []

    for ep in blended_episodes:
        try:
            audio_url = None

            for link in ep.get("links", []):
                if link.get("type") == "audio/mpeg":
                    audio_url = link.get("href")
                    break

            if not audio_url:
                ep["local_audio"] = None
                continue

            filename = download_episode_audio(audio_url)

            if filename:
                ep["local_audio"] = f"/audio/{filename}"
                full_path = str(RAW_DIR / filename)
                clip_paths.append(full_path)
            else:
                ep["local_audio"] = None

        except Exception as e:
            print(f"⚠️ Download fail: {e}")
            ep["local_audio"] = None

    # -------------------------------------------------
    # ✅ 5. AI (NOW USING CHUNKS, NOT RAW SUMMARY)
    # -------------------------------------------------
    ai_output = None

    if enable_ai:
        try:
            segments = []

            for ep in blended_episodes:
                raw = (
                    ep.get("transcript")
                    or ep.get("summary")
                    or ep.get("description")
                )

                cleaned = clean_text(raw)

                if cleaned:
                    chunks = split_into_chunks(cleaned)
                    segments.extend(chunks[:2])  # ✅ multi-idea extraction

            if segments:
                clusters = [
                    {"id": i + 1, "segments": [seg]}
                    for i, seg in enumerate(segments[:3])
                ]

                print("\n🧠 CLUSTERS:")
                print(clusters)

                ai_output = process_clusters(clusters)

        except Exception as e:
            print(f"⚠️ AI error: {e}")

    # -------------------------------------------------
    # ✅ 6. AUDIO PIPELINE (FALLBACK SAFE)
    # -------------------------------------------------
    final_audio = None

    try:
        narration_paths: List[str] = []
        audio_sequence: List[str] = []

        # ✅ TTS
        if ai_output:
            for cluster in ai_output:
                narration = cluster.get("narration")

                if not narration:
                    continue

                try:
                    path = generate_audio(narration)
                    narration_paths.append(path)
                except Exception:
                    print("⚠️ TTS failed — skipping narration")

        if narration_paths:

            if clip_paths:
                print("🎧 Narration + clips mode")

                for i in range(len(narration_paths)):
                    audio_sequence.append(narration_paths[i])

                    if i < len(clip_paths):
                        audio_sequence.append(clip_paths[i])

            else:
                print("⚠️ No clips — narration only")
                audio_sequence = narration_paths

            final_filename = stitch_blendz(audio_sequence)
            final_audio = f"/audio/final/{final_filename}"

    except Exception as e:
        print(f"🔥 Audio pipeline error: {e}")
        final_audio = None

    # -------------------------------------------------
    # ✅ FINAL RESPONSE
    # -------------------------------------------------
    return {
        "mode": "subject",
        "query": query,
        "results": blended_episodes,
        "ai": ai_output,
        "clip_count": len(clip_paths),
        "final_audio": final_audio,
    }

