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
# ✅ FILTERING (UNCHANGED)
# =========================

def is_ad(text):
    t = text.lower()
    signals = [
        "sponsor","sponsored","brought to you","support for",
        "advertising","promo","promotion","partner",
        "visit",".com","www","sign up","subscribe",
        "use code","offer","free trial"
    ]
    return any(s in t for s in signals)


def dedup_key(text):
    words = text.lower().split()
    core = " ".join(words[:12])
    return hashlib.md5(core.encode()).hexdigest()


def extract_show_name(source_path):
    try:
        parts = source_path.split("/")
        if len(parts) > 2:
            return parts[-2].replace("_", " ").title()
    except:
        pass
    return "this podcast"


# =========================
# ✅ AI NARRATION
# =========================

def generate_dateline_line(context, text=None, query="", stage="middle"):

    if stage == "intro":
        prompt = f"Introduce a deeper idea about: {query}. Max 22 words."

    elif stage == "bridge":
        prompt = f"""
Previous: "{context}"
Next: "{text}"
Build curiosity. Max 18 words.
"""

    elif stage == "outro":
        prompt = f"Reflect on: {query}. Max 22 words."

    else:
        prompt = f"Guide meaning: {text}. Max 18 words."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return safe_content(response)

    except Exception as e:
        print("⚠️ GPT error:", str(e))
        return ""


# =========================
# ✅ MAIN BUILDER (UNCHANGED CORE)
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
    
    print(
        f"Lowest score: {selected_pool[0]['score']}"
    )
    print(
        f"Highest score: {selected_pool[-1]['score']}"
    )
    selected_pool = sorted(
        selected_pool,
        key=lambda x: x["score"]
    )
    selected = selected_pool[:max_segments]

   

    if len(selected) < 8:
        selected = selected_pool[:8]

    blend = []

    # ✅ INTRO
    intro = generate_dateline_line("", query=query, stage="intro")
    blend.append({"type": "narration", "text": intro})

    # ✅ FIRST
    first = selected[0]
    show_name = extract_show_name(first.get("audio_file", ""))

    blend.append({
        "type": "speaker",
        "audio_file": first["audio_file"],
        "start": first["start"],
        "end": first["end"],
        "text": first["text"]
    
    })

    # ✅ LOOP
    for i in range(1, len(selected)):
        curr = selected[i]

        blend.append({
            "type": "speaker",
            "audio_file": curr["audio_file"],
            "start": curr["start"],
            "end": curr["end"],
            "text": curr["text"]
        })

    print(f"✅ Built blend with {len(blend)} steps")
    return blend


# =========================
# ✅ RENDER AUDIO (NEW 🔥)
# =========================

def render_blend(blend):

    blend_id = str(uuid.uuid4())
    folder = f"media/blends/{blend_id}"
    os.makedirs(folder, exist_ok=True)

    files_txt = os.path.join(folder, "files.txt")

    file_list = []

    for i, step in enumerate(blend):

        if step["type"] != "speaker":
            continue

        url = step["audio_file"]
        url = url.replace("&amp;", "&")  # ✅ FIX HTML encoding

        clip_path = os.path.join(folder, f"clip_{i}.mp3")

        print(f"🎧 Extracting clip {i}")

        subprocess.run([
            "ffmpeg",
            "-y",
            "-ss", str(step["start"]),
            "-to", str(step["end"]),
            "-i", url,
            "-c", "copy",
            clip_path
        ])

        file_list.append(clip_path)

    # ✅ CONCAT FILE
    with open(files_txt, "w") as f:
        for file in file_list:
            f.write(f"file '{file}'\n")

    final_output = os.path.join(folder, "final.mp3")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", files_txt,
        "-c", "copy",
        final_output
    ])

    return final_output


# =========================
# ✅ MAIN RUN
# =========================

if __name__ == "__main__":

    query = "CRISPR gene editing"

    blend = build_blend(query)

    print("\n🎧 Rendering audio...\n")

    output = render_blend(blend)

    print(f"\n✅ FINAL AUDIO FILE: {output}")















