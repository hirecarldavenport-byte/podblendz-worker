import faiss
import numpy as np
import sqlite3
import json
from openai import OpenAI

# ✅ CONFIG
DB_PATH = "podcast_pal.db"
INDEX_FILE = "podcast_index.faiss"
ID_MAP_FILE = "id_map.json"
MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
LIMIT = 5000   # ✅ change later (set to None for full run)

client = OpenAI()

# ✅ LOAD CHUNKS FROM DB
def load_chunks(limit=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT id, text FROM chunks"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    chunks = [{"id": r[0], "text": r[1]} for r in rows]

    print(f"✅ Loaded {len(chunks)} chunks from DB")
    return chunks


# ✅ GET EMBEDDING
def get_embedding(text):
    response = client.embeddings.create(
        model=MODEL,
        input=text
    )
    return response.data[0].embedding


# ✅ MAIN RUN FUNCTION
def run():
    # ✅ Load data
    chunks = load_chunks(LIMIT)

    # ✅ Initialize FAISS index
    dim = 1536
    index = faiss.IndexFlatL2(dim)

    # ✅ Storage
    id_map = []
    batch_embeddings = []

    print("🚀 Starting embedding + FAISS ingestion...")

    # ✅ Process chunks
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk["text"])

        batch_embeddings.append(embedding)
        id_map.append(chunk["id"])

        # ✅ Batch insert
        if len(batch_embeddings) == BATCH_SIZE:
            vectors = np.array(batch_embeddings).astype("float32")
            index.add(vectors)

            print(f"✅ Added {len(id_map)} vectors")

            batch_embeddings = []

    # ✅ Handle remainder
    if batch_embeddings:
        vectors = np.array(batch_embeddings).astype("float32")
        index.add(vectors)

    print(f"✅ Final total vectors: {index.ntotal}")

    # ✅ Save FAISS index
    faiss.write_index(index, INDEX_FILE)

    # ✅ Save ID map
    with open(ID_MAP_FILE, "w") as f:
        json.dump(id_map, f)

    print("✅ Saved FAISS index + ID map")
    print("🎉 DONE")


if __name__ == "__main__":
    run()