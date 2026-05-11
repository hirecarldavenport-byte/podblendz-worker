# podpal/ai/narration.py#from podpal.ai.prompts import build_narration_prompt
from podpal.ai.prompts import build_narration_prompt
from podpal.ai.openai_client import call_gpt

def generate_narration(label, description, segments):
    """
    Generates narration text for a cluster
    """

    samples = "\n\n".join(segments[:5])

    prompt = build_narration_prompt(label, description, samples)

    narration = call_gpt(prompt)

    return narration
