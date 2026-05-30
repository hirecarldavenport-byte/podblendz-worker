import faiss
import numpy as np

dim = 1536
index = faiss.IndexFlatL2(dim)

# create dummy vectors
vectors = np.random.rand(1000, dim).astype("float32")

index.add(vectors)

print("Total vectors in index:", index.ntotal)

# search test
query = np.random.rand(1, dim).astype("float32")
D, I = index.search(query, k=5)

print("Top results indices:", I)