# podpal/ai/openai_client.py

from __future__ import annotations

import os
import json
from typing import Union, Dict, Any

from dotenv import load_dotenv

# -------------------------------------------------
# ✅ Load environment variables
# -------------------------------------------------
load_dotenv()


# -------------------------------------------------
# ✅ Safe OpenAI import + client init
# -------------------------------------------------
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


API_KEY = os.getenv("OPENAI_API_KEY")

client = None

if OpenAI and API_KEY:
    client = OpenAI(api_key=API_KEY)
else:
    print("⚠️ OpenAI not configured — AI features will be disabled.")


# -------------------------------------------------
# ✅ Helper: Clean GPT output
# -------------------------------------------------
def _clean_response(content: str) -> str:
    """
    Removes markdown code blocks and extra formatting.
    """

    content = content.strip()

    # Remove ``` blocks
    if content.startswith("```"):
        content = content.strip("`")

        # Remove optional language tag (json, text, etc.)
        if content.startswith("json"):
            content = content[4:].strip()

    return content


# -------------------------------------------------
# ✅ MAIN FUNCTION
# -------------------------------------------------
def call_gpt(prompt: str) -> Union[Dict[str, Any], str]:
    """
    Sends prompt to GPT and returns:

    - dict (parsed JSON when possible)
    - string (fallback)

    Raises:
        RuntimeError if client is not initialized
    """

    if client is None:
        raise RuntimeError("OpenAI client not initialized — check API key")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )

        content = response.choices[0].message.content

    except Exception as e:
        print(f"🔥 OpenAI request failed: {e}")
        raise RuntimeError("GPT request failed") from e

    if not content:
        return "No response from model."

    # ✅ Clean formatting
    content = _clean_response(content)

    # ✅ Try JSON parse
    try:
        return json.loads(content)
    except Exception:
        return content


