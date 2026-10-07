import asyncio
import time
from typing import List, Dict, Any
from app.core.dependencies import _get_db_adapter, _get_embedder_adapter, _get_llm_adapter, _get_reranker_adapter
from app.services.retrieval_engine import RetrievalEngine
from app.core.logger import logger

# Example benchmark dataset
# In a real scenario, you'd load this from a JSON/CSV file.
# Each query maps to the expected (document_id, chunk_index) that answers it.
BENCHMARK_DATA = [
    {
        "query": "What is the employee's PF contribution?",
        "expected": [("doc-1", 5)]
    },
    {
        "query": "What is the company's Q3 revenue?",
        "expected": [("doc-2", 12)]
    },
    {
        "query": "Are NDAs required for contractors?",
        "expected": [("doc-3", 2)]
    },
    # Add more factual, numeric, legal, financial, and table queries here.
]

def calculate_mrr(retrieved_docs: List[Dict], expected: List[tuple]) -> float:
    for rank, doc in enumerate(retrieved_docs):
        doc_identity = (doc.get("document_id"), doc.get("chunk_index"))
        if doc_identity in expected:
            return 1.0 / (rank + 1)
    return 0.0

def calculate_recall(retrieved_docs: List[Dict], expected: List[tuple], k: int) -> float:
    top_k_docs = retrieved_docs[:k]
    for doc in top_k_docs:
        doc_identity = (doc.get("document_id"), doc.get("chunk_index"))
        if doc_identity in expected:
            return 1.0
    return 0.0

async def run_benchmark(box_id: str):
    print("Initializing components...")
    db = _get_db_adapter()
    embedder = _get_embedder_adapter()
    llm = _get_llm_adapter()
    reranker = _get_reranker_adapter()

    retrieval_engine = RetrievalEngine(
        db=db,
        embedder=embedder,
        llm=llm,
        reranker=reranker,
        retrieval_top_k=20,
        reranker_top_k=10,
        enable_hyde=False,
        enable_multi_query=False
    )

    print(f"Running benchmark on {len(BENCHMARK_DATA)} queries...\n")
    
    total_mrr = 0.0
    total_recall_5 = 0.0
    total_recall_10 = 0.0
    
    total_retrieval_time = 0.0
    
    for item in BENCHMARK_DATA:
        query = item["query"]
        expected = item["expected"]
        
        start_time = time.time()
        
        # Execute retrieval
        results = retrieval_engine.retrieve_documents(search_query=query, box_id=box_id)
        
        latency = time.time() - start_time
        total_retrieval_time += latency
        
        # Calculate metrics
        mrr = calculate_mrr(results, expected)
        r5 = calculate_recall(results, expected, 5)
        r10 = calculate_recall(results, expected, 10)
        
        total_mrr += mrr
        total_recall_5 += r5
        total_recall_10 += r10
        
        print(f"Query: '{query}'")
        print(f"  Latency: {latency:.3f}s")
        print(f"  MRR: {mrr:.3f}, Recall@5: {r5:.1f}, Recall@10: {r10:.1f}")
        print("-" * 40)

    n = len(BENCHMARK_DATA)
    if n > 0:
        print("\n=== BENCHMARK RESULTS ===")
        print(f"Total Queries: {n}")
        print(f"Average Latency: {total_retrieval_time / n:.3f}s")
        print(f"Mean Reciprocal Rank (MRR): {total_mrr / n:.3f}")
        print(f"Recall@5: {total_recall_5 / n:.3f}")
        print(f"Recall@10: {total_recall_10 / n:.3f}")

if __name__ == "__main__":
    # Specify the Box ID to test against. 
    # Must contain the documents referenced in BENCHMARK_DATA.
    TEST_BOX_ID = "00000000-0000-0000-0000-000000000000" 
    
    # Run the async benchmark
    asyncio.run(run_benchmark(TEST_BOX_ID))
