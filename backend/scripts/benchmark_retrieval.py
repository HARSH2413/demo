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
    {
        "query": "Who is the CEO of the organization?",
        "expected": [("doc-1", 1)]
    },
    {
        "query": "What are the core hours for working?",
        "expected": [("doc-4", 8)]
    },
    {
        "query": "What is the refund policy for canceled flights?",
        "expected": [("doc-5", 3)]
    },
    {
        "query": "Does the health insurance cover dental?",
        "expected": [("doc-6", 14)]
    },
    {
        "query": "What is the maximum allowed PTO?",
        "expected": [("doc-1", 10)]
    },
    {
        "query": "How many days notice is required for resignation?",
        "expected": [("doc-7", 4)]
    },
    {
        "query": "What was the total expenditure in 2024?",
        "expected": [("doc-2", 15)]
    },
    {
        "query": "What are the rules for remote work?",
        "expected": [("doc-8", 2)]
    },
    {
        "query": "Is there a budget for home office equipment?",
        "expected": [("doc-8", 5)]
    },
    {
        "query": "What is the SLA for sev-1 incidents?",
        "expected": [("doc-9", 1)]
    },
    {
        "query": "Who is the primary contact for HR issues?",
        "expected": [("doc-10", 0)]
    },
    {
        "query": "What is the performance review schedule?",
        "expected": [("doc-11", 6)]
    },
    {
        "query": "Are bonuses guaranteed?",
        "expected": [("doc-12", 9)]
    },
    {
        "query": "What is the penalty for early termination of the contract?",
        "expected": [("doc-13", 20)]
    },
    {
        "query": "Is travel time compensated?",
        "expected": [("doc-14", 7)]
    },
    {
        "query": "Can I expense client dinners?",
        "expected": [("doc-15", 3)]
    },
    {
        "query": "What is the procedure for filing a grievance?",
        "expected": [("doc-16", 11)]
    }
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
    total_db_search_time = 0.0
    total_reranker_time = 0.0
    
    # Patch the engine to record latencies
    original_multi_query_search = retrieval_engine._multi_query_search
    original_rerank = retrieval_engine.reranker.rerank if retrieval_engine.reranker else None
    
    def patched_multi_query_search(*args, **kwargs):
        t0 = time.time()
        res = original_multi_query_search(*args, **kwargs)
        nonlocal db_search_latency
        db_search_latency = time.time() - t0
        return res
        
    def patched_rerank(*args, **kwargs):
        t0 = time.time()
        res = original_rerank(*args, **kwargs)
        nonlocal reranker_latency
        reranker_latency = time.time() - t0
        return res
        
    retrieval_engine._multi_query_search = patched_multi_query_search
    if retrieval_engine.reranker:
        retrieval_engine.reranker.rerank = patched_rerank
    
    for item in BENCHMARK_DATA:
        query = item["query"]
        expected = item["expected"]
        
        db_search_latency = 0.0
        reranker_latency = 0.0
        
        start_time = time.time()
        
        # Execute retrieval
        results = retrieval_engine.retrieve_documents(search_query=query, box_id=box_id)
        
        latency = time.time() - start_time
        total_retrieval_time += latency
        total_db_search_time += db_search_latency
        total_reranker_time += reranker_latency
        
        # Calculate metrics
        mrr = calculate_mrr(results, expected)
        r5 = calculate_recall(results, expected, 5)
        r10 = calculate_recall(results, expected, 10)
        
        total_mrr += mrr
        total_recall_5 += r5
        total_recall_10 += r10
        
        print(f"Query: '{query}'")
        print(f"  Total Latency: {latency:.3f}s | DB Search: {db_search_latency:.3f}s | Reranker: {reranker_latency:.3f}s")
        print(f"  MRR: {mrr:.3f}, Recall@5: {r5:.1f}, Recall@10: {r10:.1f}")
        print("-" * 40)

    n = len(BENCHMARK_DATA)
    if n > 0:
        print("\n=== BENCHMARK RESULTS ===")
        print(f"Total Queries: {n}")
        print(f"Average Total Latency: {total_retrieval_time / n:.3f}s")
        print(f"Average DB Search Latency: {total_db_search_time / n:.3f}s")
        print(f"Average Reranker Latency: {total_reranker_time / n:.3f}s")
        print(f"Mean Reciprocal Rank (MRR): {total_mrr / n:.3f}")
        print(f"Recall@5: {total_recall_5 / n:.3f}")
        print(f"Recall@10: {total_recall_10 / n:.3f}")

if __name__ == "__main__":
    # Specify the Box ID to test against. 
    # Must contain the documents referenced in BENCHMARK_DATA.
    TEST_BOX_ID = "00000000-0000-0000-0000-000000000000" 
    
    # Run the async benchmark
    asyncio.run(run_benchmark(TEST_BOX_ID))
