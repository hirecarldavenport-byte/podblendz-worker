# scripts/test_tts.py

import asyncio
import edge_tts

async def main():

    communicate = edge_tts.Communicate(
        text="Hello PodBlendz",
        voice="en-US-AriaNeural"
    )

    await communicate.save(
        "media/test_tts.mp3"
    )

asyncio.run(main())

print("DONE")