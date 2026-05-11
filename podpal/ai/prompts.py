# podpal/ai/prompts.py

def build_cluster_label_prompt(text_samples):
    return f"""
You are organizing podcast content into themes.

IMPORTANT:


Here are excerpts:
- Always respond in English
- Ignore the original language of the content

{text_samples}

Return JSON:
{{
  "label": "...",
  "description": "..."
}}
"""


def build_narration_prompt(label, description, segments):
    return f"""
You are a professional podcast narrator.

IMPORTANT:
- Always write in English
- Translate ideas if needed
- Do not use any other language

Theme: {label}
Description: {description}

Source excerpts:
{segments}

Write a smooth, natural-sounding narration.
"""