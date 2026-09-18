import sys
import os

# Ensure backend is in PYTHONPATH
sys.path.append(os.getcwd())

from app.infrastructure.reranker_adapter import FastEmbedRerankerAdapter

def test():
    reranker = FastEmbedRerankerAdapter()
    query = "What is the capital of France?"
    documents = [
        {"content": "Paris is the capital of France."},
        {"content": "The quick brown fox jumps over the lazy dog."},
        {"content": "France is a country in Europe. Its capital is Paris, which is known for the Eiffel Tower."}
    ]
    
    scored = reranker.rerank(query, documents)
    print("\n--- RESULTS ---")
    for doc in scored:
        print(f"Score: {doc['rerank_score']:.4f} | Content: {doc['content']}")

if __name__ == "__main__":
    test()
