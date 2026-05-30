from search_faiss import search

# ✅ Test query
query = "fear vs courage in decision making"

results = search(query)

print("\n✅ TOP RESULTS:\n")

for i, r in enumerate(results[:5]):
    print(f"{i+1}. {r['text'][:150]}\n")
    print(f"   Source: {r['source']}")
    print(f"   Score: {r['score']}\n")