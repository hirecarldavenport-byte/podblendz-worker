# podpal/ai/prompts.py

def build_cluster_label_prompt(text_samples):
    return f"""
You are organizing podcast content into themes.

Here are excerpts:

{text_samples}

Return JSON:
{{
  "label": "...",
  "description": "..."
}}
"""


def build_narration_prompt(label, description, segments):
    return f"""
You are a podcast narrator.

Theme: {label}
Description: {description}

Source excerpts:
{segments}

Write a smooth, natural-sounding narration.
"""