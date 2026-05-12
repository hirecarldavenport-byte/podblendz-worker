# podpal/audio/tts.py

from __future__ import annotations

import os
import uuid
import asyncio
from datetime import datetime
from typing import Optional

import edge_tts
import logging


# -------------------------------------------------
# ✅ Logging cleanup
# -------------------------------------------------
logging.getLogger("edge_tts").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


# -------------------------------------------------
# ✅ Helper: Safe async execution (FIXES FastAPI crash)
# -------------------------------------------------
async def _run_save(communicate: edge_tts.Communicate, output_path: str) -> None:
    await communicate.save(output_path)


def _run_async_task(coro):
    """
    Safely run async code from sync context (FastAPI-safe)
    """
    try:
        loop = asyncio.get_running_loop()
        # ✅ already in event loop → run task properly
        return loop.create_task(coro)
    except RuntimeError:
        # ✅ no loop → safe to run
        return asyncio.run(coro)


# -------------------------------------------------
# ✅ MAIN TTS FUNCTION
# -------------------------------------------------
def generate_audio(
    text: str,
    voice: str = "en-US-GuyNeural",
    output_dir: str = "audio/tts",   # ✅ FIXED path
    filename_prefix: str = "blend",
) -> str:
    """
    Generate TTS audio using Microsoft Edge TTS.

    Returns:
        Absolute path to generated MP3 file.
    """

    # ✅ Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)

    # ✅ Unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{filename_prefix}_{timestamp}_{unique_id}.mp3"

    output_path = os.path.abspath(os.path.join(output_dir, filename))

    print(f"🔊 Generating TTS → {output_path}")

    try:
        # ✅ Create TTS communicate object
        communicate = edge_tts.Communicate(text=text, voice=voice)

        # ✅ Run async safely (NO asyncio.run crash)
        coro = _run_save(communicate, output_path)
        result = _run_async_task(coro)

        # ✅ If task returned, wait for it
        if asyncio.isfuture(result):
            asyncio.get_event_loop().run_until_complete(result)

    except Exception as e:
        print(f"🔥 TTS ERROR: {e}")
        raise RuntimeError("TTS generation failed") from e

    # -------------------------------------------------
    # ✅ Validate output
    # -------------------------------------------------
    if not os.path.exists(output_path):
        raise RuntimeError("TTS file was not created")

    if os.path.getsize(output_path) == 0:
        try:
            os.remove(output_path)
        except Exception:
            pass
        raise RuntimeError("TTS output file is empty")

    print(f"✅ TTS complete → {output_path}")

    return output_path
