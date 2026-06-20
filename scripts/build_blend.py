from scripts.search_faiss import search
from openai import OpenAI
import os
import json
import hashlib
import subprocess
import uuid

# ✅ INIT
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# =========================
# ✅ HELPERS
# =========================

def shorten(text, max_words=40):
    return " ".join(text.split()[:max_words])


def safe_content(response):
    try:
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        print("⚠️ safe_content error:", str(e))
        return ""


# =========================
# ✅ FILTERING
# =========================

def is_ad(text):
    t = text.lower()

    signals = [
        "sponsor", "sponsored", "brought to you", "support for",
        "advertising", "promo", "promotion", "partner",
        "visit", ".com", "www", "sign up", "subscribe",
        "use code", "offer", "free trial"
    ]

    return any(s in t for s in signals)


def dedup_key(text):
    words = text.lower().split()
    core = " ".join(words[:12])

    return hashlib.md5(
        core.encode()
    ).hexdigest()


def extract_show_name(source_path):
    try:
        parts = source_path.split("/")

        if len(parts) > 2:
            return parts[-2].replace("_", " ").title()

    except Exception:
        pass

    return "this podcast"


# =========================
# ✅ TONE DETECTION
# =========================

def get_tone(query):
    q = query.lower()
    if any(x in q for x in [
        "dementia",
        "alzheimer",
        "brain",
        "memory",
        "mental health",
        "health",
        "longevity"
    ]):
        return (
            "warm, thoughtful, hopeful, human"
        )
    if any(x in q for x in [
        "startup",
        "business",
        "leadership",
        "venture",
        "marketing",
        "sales"
    ]):
        return (
            "confident, practical, insightful"
        )
    if any(x in q for x in [
        "ai",
        "artificial intelligence",
        "machine learning",
        "robotics",
        "automation"
    ]):
        return (
            "curious, futuristic, innovative"
        )
    if any(x in q for x in [
        "relationship",
        "dating",
        "marriage",
        "parenting"
    ]):
        return (
            "reflective, conversational, relatable"
        )
    return (
        "engaging, intelligent, conversational"
    )

# =========================
# ✅ AI NARRATION
# =========================



def generate_dateline_line(
    context,
    text=None,
    query="",
    stage="middle"
):
    tone = get_tone(query)

    if stage == "intro":

        prompt = f"""
        Topic:
        {query}

        Tone:
        {tone}
        Create a compelling opening.

        Do not sound academic.
        Do not sound like a documentary.
        Sound natural and engaging.
        Maximum 22 words.
        """

    elif stage == "bridge":

        prompt = f"""
Previous: "{context}"

Next: "{text}"

Build curiosity.

Max 18 words.
"""

    elif stage == "outro":

        prompt = f"""
        Topic:
        {query}
        Key ideas discussed:
        {context}
        
        Create a final takeaway.
        Do not summarize mechanically.
        End with a memorable insight.
        Maximum 45 words.
        Sound human.
        """

    else:
        prompt = f"""
        Topic:
        {query}
        Tone:
        {tone}
        Create a short observation that helps
        the listener connect ideas.
        Do not summarize.
        Do not sound academic.
        Maximum 18 words.
        Content:
        {text}
        """

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return safe_content(response)

    except Exception as e:

        print("⚠️ GPT error:", str(e))
        return ""


# =========================
# ✅ MAIN BUILDER
# =========================

def build_blend(query, max_segments=20):

    print(f"\n🎧 Building Blend: {query}\n")

    results = search(query, k=120) or []

    selected_pool = []
    seen = set()
    source_counts = {}

    skipped_missing_audio = 0

    MAX_PER_SOURCE = 2

    for r in results:

        text = r.get("text", "").strip()
        start = r.get("start")
        end = r.get("end")
        source = r.get("audio_file")

        if not source:
            skipped_missing_audio += 1
            continue

        if start is None or end is None:
            continue

        duration = end - start

        if not text or duration < 3:
            continue

        if is_ad(text):
            continue

        key = dedup_key(text)

        if key in seen:
            continue

        seen.add(key)

        count = source_counts.get(source, 0)

        if count >= MAX_PER_SOURCE:
            continue

        source_counts[source] = count + 1

        selected_pool.append(r)

    print(f"✅ Retrieved {len(selected_pool)} usable segments")
    print(f"⚠️ Skipped {skipped_missing_audio} missing audio")

    if not selected_pool:
        return []

    # =========================
    # ✅ SCORE DIAGNOSTICS
    # =========================

    scores = [
        item["score"]
        for item in selected_pool
        if "score" in item
    ]

    if scores:

        print(f"Min score: {min(scores)}")
        print(f"Max score: {max(scores)}")

    # =========================
    # ✅ DISTANCE SORT
    # =========================

    selected_pool = sorted(
        selected_pool,
        key=lambda x: x["score"]
    )

    print(
        f"After ascending sort -> first score: "
        f"{selected_pool[0]['score']}"
    )

    print(
        f"After ascending sort -> last score: "
        f"{selected_pool[-1]['score']}"
    )

    selected = selected_pool[:max_segments]

    total_duration = 0
    for item in selected:
        total_duration += (
            item["end"] -
            item["start"]
        )
    print(
            f"Total clip duration:"
            f" {round(total_duration,1)} sec"
        )

    if len(selected) < 8:
        selected = selected_pool[:8]

    blend = []

    # =========================
    # ✅ INTRO
    # =========================

    intro = generate_dateline_line(
        "",
        query=query,
        stage="intro"
    )

    blend.append({
        "type": "narration",
        "text": intro
    })

    # =========================
    # ✅ FIRST CLIP
    # =========================

    first = selected[0]
    print("\n🔍 FIRST CLIP KEYS")
    print(first.keys())

    print("\n✅ First Selected Clip")
    print(
        "Podcast:",
        first.get("podcast_title")
    )
    print(
        "Episode:",
        first.get("episode_title")
    )

    blend.append({
        "type": "speaker",

        "audio_file": first["audio_file"],
        "start": first["start"],
        "end": first["end"],
        "text": first["text"],

        # Metadata
        "episode_id": first.get("episode_id"),
        "episode_title": first.get("episode_title"),
        "episode_description": first.get("episode_description"),
        "published": first.get("published"),

        "podcast_id": first.get("podcast_id"),
        "podcast_title": first.get("podcast_title"),
        "podcast_description": first.get("podcast_description")
    })

    # =========================
    # ✅ REMAINING CLIPS
    # =========================

    for i in range(1, len(selected)):

        curr = selected[i]

        blend.append({
            "type": "speaker",

            "audio_file": curr["audio_file"],
            "start": curr["start"],
            "end": curr["end"],
            "text": curr["text"],

            # Metadata
            "episode_id": curr.get("episode_id"),
            "episode_title": curr.get("episode_title"),
            "episode_description": curr.get("episode_description"),
            "published": curr.get("published"),

            "podcast_id": curr.get("podcast_id"),
            "podcast_title": curr.get("podcast_title"),
            "podcast_description": curr.get("podcast_description")
        })

        
# =========================
# ✅ OUTRO
# =========================

    recent_context = "\n".join([
        shorten(item["text"], 20)
        for item in selected[-5:]
        ])
    
    outro = generate_dateline_line(
        recent_context,
        query=query,
        stage="outro"
    
    )

    blend.append({
        "type": "narration",
        "text": outro
})
    print(
        f"✅ Built blend with {len(blend)} steps"
    )
    return blend

# =========================
# ✅ RENDER AUDIO
# =========================

def render_blend(blend):

    blend_id = str(uuid.uuid4())

    folder = f"media/blends/{blend_id}"

    os.makedirs(
        folder,
        exist_ok=True
    )

    files_txt = os.path.join(
        folder,
        "files.txt"
    )

    file_list = []

    for i, step in enumerate(blend):

        if step["type"] != "speaker":
            continue

        url = step["audio_file"]

        url = url.replace(
            "&amp;amp;",
            "&amp;"
        )

        clip_path = os.path.join(
            folder,
            f"clip_{i}.mp3"
        )

        print(f"🎧 Extracting clip {i}")

        subprocess.run([
            "ffmpeg",
            "-y",
            "-ss",
            str(step["start"]),
            "-to",
            str(step["end"]),
            "-i",
            url,
            "-c",
            "copy",
            clip_path
        ])

        file_list.append(clip_path)

    with open(files_txt, "w") as f:

        for file in file_list:
            filename = os.path.basename(file)
            f.write(
                f"file '{filename}'\n"
                )

    final_output = os.path.join(
        folder,
        "final.mp3"
    )

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        files_txt,
        "-c",
        "copy",
        final_output
    ])

    return final_output


# =========================
# ✅ MAIN RUN
# =========================

if __name__ == "__main__":

    query = "CRISPR gene editing"

    blend = build_blend(query)

    print(json.dumps(blend[-1], indent=2))

    print("\n🎧 Rendering audio...\n")

    output = render_blend(blend)

    print(f"\n✅ FINAL AUDIO FILE: {output}")















