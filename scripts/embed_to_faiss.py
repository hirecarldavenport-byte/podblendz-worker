import faiss
import numpy as np
import json

# ✅ your embedding dim
DIM = 1536

# ✅ create index
index = faiss.IndexFlatL2(DIM)

# ✅ storage for mapping FAISS index → your IDs
id_map = []

# ✅ replace this with YOUR chunk loader
def load_chunks():
    # Example structure:
    # return [{"id": "chunk_1", "text": "..."}, ...]
    raise NotImplementedError


# ✅ replace with YOUR embedding function
def get_embedding(text):
    raise NotImplementedError


def run():
    chunks = load_chunks()[:5000]

    batch_embeddings = []

    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk["text"])

        batch_embeddings.append(embedding)
        id_map.append(chunk["id"])

        # batch add (same idea as Pinecone batching)
        if len(batch_embeddings) == 100:
            vectors = np.array(batch_embeddings).astype("float32")
            index.add(vectors)

            print(f"✅ Added {len(id_map)} vectors")

            batch_embeddings = []

    # add remaining
    if batch_embeddings:
        vectors = np.array(batch_embeddings).astype("float32")
        index.add(vectors)

    print("✅ Final total:", index.ntotal)

    # ✅ SAVE index
    faiss.write_index(index, "podcast_index.faiss")

    # ✅ SAVE ID mapping
    with open("id_map.json", "w") as f:
        json.dump(id_map, f)

    print("✅ Saved FAISS index + ID map")


if __name__ == "__main__":
    run()