from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple, List
from pydub import AudioSegment


# =========================
# ✅ MODELS
# =========================

@dataclass
class ClipRange:
    clip_id: str   # URL or local path
    start_ms: int
    end_ms: int
    is_narration: bool = False   # ✅ NEW


@dataclass
class AudioOptions:
    output_format: str = "mp3"
    bitrate_kbps: int = 160
    crossfade_ms: int = 300
    fade_in_ms: int = 50
    fade_out_ms: int = 50

    music_bed: Optional[str] = None
    music_bed_gain_db: float = -20.0

    narration_duck_db: float = -12.0   # ✅ NEW
    normalize_audio: bool = True       # ✅ NEW


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

        segments: List[AudioSegment] = []

        # -------------------------
        # ✅ LOAD + PROCESS SEGMENTS
        # -------------------------
        for c in clips:
            path = self._resolve_audio(c.clip_id)

            seg = self._load_and_trim(
                path,
                int(c.start_ms),
                int(c.end_ms)
            )

            # ✅ Normalize individual clips
            if options.normalize_audio:
                seg = self._normalize(seg)

            # ✅ Narration ducking prep
            if c.is_narration:
                seg = seg.apply_gain(+2)  # slight boost

            # ✅ Fades
            if options.fade_in_ms > 0:
                seg = seg.fade_in(options.fade_in_ms)

            if options.fade_out_ms > 0:
                seg = seg.fade_out(options.fade_out_ms)

            segments.append(seg)

        if len(segments) == 0:
            raise ValueError("No audio segments to stitch")

        # -------------------------
        # ✅ CONCATENATION
        # -------------------------
        timeline = segments[0]

        for i in range(1, len(segments)):
            prev = segments[i - 1]
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
        # ✅ MUSIC BED + DUCKING
        # -------------------------
        if options.music_bed:
            bed = AudioSegment.from_file(options.music_bed)

            bed_full = self._loop_to_length(bed, len(timeline))

            # ✅ Force clean type (NO Pylance issues)
            assert isinstance(bed_full, AudioSegment)

            # ✅ Apply base gain
            bed_full = bed_full.apply_gain(options.music_bed_gain_db)

            # ✅ Duck music slightly overall
            bed_full = bed_full - 3

            timeline = timeline.overlay(bed_full)

        # -------------------------
        # ✅ FINAL NORMALIZATION
        # -------------------------
        if options.normalize_audio:
            timeline = self._normalize(timeline)

        # -------------------------
        # ✅ EXPORT
        # -------------------------
        ext = options.output_format.lower()
        out_file = os.path.join(out_dir, f"final.{ext}")

        if ext == "mp3":
            timeline.export(out_file, format="mp3", bitrate=f"{options.bitrate_kbps}k")
        else:
            timeline.export(out_file, format="wav")

        return out_file, len(timeline)

    # =========================
    # ✅ AUDIO RESOLUTION
    # =========================

    def _resolve_audio(self, source: str) -> str:
        if source.startswith("http"):
            return self._download_and_cache(source)

        if os.path.exists(source):
            return source

        raise FileNotFoundError(f"Invalid source: {source}")

    def _download_and_cache(self, url: str) -> str:
        filename = url.split("?")[0].split("/")[-1]
        local_path = os.path.join(self.cache_dir, filename)

        if os.path.exists(local_path):
            return local_path

        try:
            print(f"⬇️ Downloading {filename}")

            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            return local_path

        except Exception as e:
            raise RuntimeError(f"Download failed: {e}")

    # =========================
    # ✅ HELPERS
    # =========================

    def _load_and_trim(self, path, start_ms, end_ms):

        if end_ms <= start_ms:
            raise ValueError(f"Invalid range {start_ms} → {end_ms}")

        audio = AudioSegment.from_file(path)

        s = max(0, int(start_ms))
        e = min(len(audio), int(end_ms))

        segment = audio[s:e]  # ✅ NO typing here
        return segment

    def _loop_to_length(self, seg, target_ms):

        current = AudioSegment.silent(
            duration=0,
            frame_rate=seg.frame_rate
        )

        while len(current) < target_ms:
            current = current + seg

        if len(current) <= target_ms:
            return current

        trimmed = current[:target_ms]
        return trimmed

    def _normalize(self, seg: AudioSegment) -> AudioSegment:
        """
        Simple normalization (not LUFS, but good for v1)
        """
        change = -20.0 - seg.dBFS if seg.dBFS != float('-inf') else 0
        return seg.apply_gain(change)

