from __future__ import annotations

import os
import sys
import requests
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

# =========================
# ✅ FIX: Python 3.12 audioop removal
# =========================
try:
    import audioop
except ImportError:
    import audioop_lts as audioop  # type: ignore
    sys.modules["audioop"] = audioop

from pydub import AudioSegment


# =========================
# ✅ MODELS
# =========================

@dataclass
class ClipRange:
    clip_id: str   # URL or local file path
    start_ms: int
    end_ms: int


@dataclass
class AudioOptions:
    output_format: str = "mp3"
    bitrate_kbps: int = 160
    crossfade_ms: int = 300
    fade_in_ms: int = 50
    fade_out_ms: int = 50
    music_bed: Optional[str] = None
    music_bed_gain_db: float = -18.0


# =========================
# ✅ BUILDER
# =========================

class AudioBuilder:

    def __init__(self, media_root: str = "media"):
        self.media_root = media_root
        self.cache_dir = os.path.join(media_root, "cache")

        os.makedirs(self.media_root, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    # =========================
    # ✅ MAIN BUILD
    # =========================

    def build(
        self,
        blend_id: str,
        clips: Iterable[ClipRange],
        options: AudioOptions,
    ) -> Tuple[str, int]:

        out_dir = os.path.join(self.media_root, "blends", blend_id)
        os.makedirs(out_dir, exist_ok=True)

        segments: list[AudioSegment] = []

        print("🎧 Building audio timeline...")

        # -------------------------
        # ✅ LOAD + TRIM
        # -------------------------
        for c in clips:
            path = self._resolve_audio(c.clip_id)

            audio = AudioSegment.from_file(path)

            start = max(0, int(c.start_ms))
            end = min(len(audio), int(c.end_ms))

            if end <= start:
                continue

            segment = audio[start:end]

            if options.fade_in_ms > 0:
                segment = segment.fade_in(options.fade_in_ms)

            if options.fade_out_ms > 0:
                segment = segment.fade_out(options.fade_out_ms)

            segments.append(segment)

        if not segments:
            raise ValueError("No valid audio segments")

        # -------------------------
        # ✅ STITCH
        # -------------------------
        timeline = segments[0]

        for i in range(1, len(segments)):
            prev = timeline
            curr = segments[i]

            cf = min(
                options.crossfade_ms,
                len(prev) // 2,
                len(curr) // 2
            )

            if cf > 0:
                timeline = timeline.append(curr, crossfade=cf)
            else:
                timeline = timeline + curr

        # -------------------------
        # ✅ MUSIC BED
        # -------------------------
        if options.music_bed:
            bed = AudioSegment.from_file(options.music_bed)

            bed_full = self._loop_audio(bed, len(timeline))

            # ✅ Fix Pylance type confusion
            assert isinstance(bed_full, AudioSegment)

            bed_full = bed_full.apply_gain(options.music_bed_gain_db)

            timeline = timeline.overlay(bed_full)

        # -------------------------
        # ✅ EXPORT
        # -------------------------
        ext = options.output_format.lower()
        out_file = os.path.join(out_dir, f"final.{ext}")

        if ext == "mp3":
            timeline.export(out_file, format="mp3", bitrate=f"{options.bitrate_kbps}k")
        else:
            timeline.export(out_file, format="wav")

        print(f"✅ Audio built: {out_file}")

        return out_file, len(timeline)

    # =========================
    # ✅ HELPERS
    # =========================

    def _resolve_audio(self, source: str) -> str:
        if source.startswith("http"):
            return self._download(source)

        if os.path.exists(source):
            return source

        raise FileNotFoundError(f"Invalid audio source: {source}")

    def _download(self, url: str) -> str:
        filename = url.split("?")[0].split("/")[-1]
        local_path = os.path.join(self.cache_dir, filename)

        if os.path.exists(local_path):
            return local_path

        print(f"⬇️ Downloading {filename}")

        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)

        return local_path

    def _loop_audio(self, seg: AudioSegment, target_ms: int):
        current = AudioSegment.silent(
            duration=0,
            frame_rate=seg.frame_rate
        )

        while len(current) < target_ms:
            current = current + seg

        if len(current) > target_ms:
            trimmed = current[:target_ms]
            return trimmed

        return current

    