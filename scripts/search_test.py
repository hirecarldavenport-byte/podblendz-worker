import os
from openai import OpenAI
from pinecone import Pinecone

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

index = pc.Index("podblendz")


def search(query, top_k=30):
    print(f"\n🔍 Searching for: {query}")

    # ✅ Step 1: Embed query
    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding

    # ✅ Step 2: Query Pinecone
    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True
    )

    print(f"\n🎯 Results (top {top_k}):\n")

    cleaned_results = []

    for match in results["matches"]:
        text = match["metadata"].get("text", "")

        # ✅ 🔥 Filter weak segments
        if (
            not text
            or len(text.strip()) < 40
            or len(text.split()) < 8
        ):
            continue

        cleaned_results.append({
            "score": match["score"],
            "text": text,
            "start": match["metadata"].get("start"),
            "end": match["metadata"].get("end"),
            "source": match["metadata"].get("source")
        })

    # ✅ ✅ Sort (extra safety)
    cleaned_results = sorted(
        cleaned_results,
        key=lambda x: x["score"],
        reverse=True
    )

    # ✅ ✅ Print clean results
    for r in cleaned_results[:10]:  # show top 10 only
        print("-----")
        print(f"Score: {r['score']:.4f}")
        print(r["text"][:200])

    print(f"\n✅ Usable results: {len(cleaned_results)}")

    return cleaned_results


if __name__ == "__main__":
    search("feeling stuck in life and what to do")