# podpal/ai/openai_client.py

from openai import OpenAI
import os
import json
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

# ✅ Create OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_gpt(prompt):
    """
    Sends a prompt to GPT and returns either:
    - dict (if JSON)
    - string (otherwise)
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )

    content = response.choices[0].message.content

    if content is None:
        return "No response from model."

    # ✅ Clean formatting (removes ```json blocks)
    content = content.strip()

    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:].strip()

    # ✅ Try to parse JSON
    try:
        return json.loads(content)
    except Exception:
        return content

