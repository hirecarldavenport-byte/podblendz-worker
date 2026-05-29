import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

text = "AI is transforming the future of humanity."

response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)

embedding = response.data[0].embedding

print(f"Vector length: {len(embedding)}")
print(embedding[:10])  # first 10 values