# podpal/ai/labeling.py# podpalpts import build_cluster_label_prompt
from podpal.ai.openai_client import call_gpt  # create this if you don’t have it
from podpal.ai.prompts import build_cluster_label_prompt

def label_cluster(segments):
    """
    Takes a list of text segments and returns a label + description
    """

    # ✅ Limit size (important)
    samples = "\n\n".join(segments[:5])

    prompt = build_cluster_label_prompt(samples)

    response = call_gpt(prompt)

    # assuming GPT returns JSON
    return response
