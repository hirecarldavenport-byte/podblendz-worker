# podpal/ai/openai_client.py

from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )

    content = response.choices[0].message.content

    # ✅ Fix: handle None safely
    if content is None:
        return "No response from model."

    # ✅ Try JSON parse (for labeling)
    try:
        return json.loads(content)
    except Exception:
        return content

