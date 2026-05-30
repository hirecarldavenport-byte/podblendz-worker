import os
from openai import OpenAI
from pinecone import Pinecone

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

index = pc.Index("podblendz")


def search(query):
    print(f"\n🔍 Searching for: {query}")

    # ✅ embed the query
    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding

    # ✅ search Pinecone
    results = index.query(
        vector=embedding,
        top_k=5,
        include_metadata=True
    )

    print("\n🎯 Results:\n")

    for match in results["matches"]:
        print("-----")
        print(f"Score: {match['score']:.4f}")
        print(match["metadata"]["text"][:200])  # preview


if __name__ == "__main__":
    search("identity transformation")