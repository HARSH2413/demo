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

async def seed_test_box(box_id: str, db, embedder):
    """
    Seeds a live Supabase box with actual chunks matching the expected results.
    """
    print(f"Seeding temporary box '{box_id}' with benchmark chunks...")
    
    import uuid
    DOCS = {f"doc-{i}": str(uuid.uuid4()) for i in range(1, 17)}
    
    # We will just insert the expected chunks directly for the benchmark queries
    # so they exist in the live DB for retrieval.
    mock_chunks = [
        {"doc": DOCS["doc-1"], "chunk": 1, "text": "The CEO of the organization is Jane Doe."},
        {"doc": DOCS["doc-1"], "chunk": 5, "text": "The employee's PF contribution is 12% of their basic salary."},
        {"doc": DOCS["doc-1"], "chunk": 10, "text": "The maximum allowed PTO is 30 days per year."},
        {"doc": DOCS["doc-2"], "chunk": 12, "text": "The company's Q3 revenue reached a record $50 million."},
        {"doc": DOCS["doc-2"], "chunk": 15, "text": "The total expenditure in 2024 was $120 million."},
        {"doc": DOCS["doc-3"], "chunk": 2, "text": "Yes, NDAs are required for all independent contractors before beginning work."},
        {"doc": DOCS["doc-4"], "chunk": 8, "text": "The core hours for working are between 10 AM and 3 PM."},
        {"doc": DOCS["doc-5"], "chunk": 3, "text": "Canceled flights are fully refunded if canceled 48 hours prior to departure."},
        {"doc": DOCS["doc-6"], "chunk": 14, "text": "The standard health insurance plan covers dental up to $2,000 annually."},
        {"doc": DOCS["doc-7"], "chunk": 4, "text": "A standard 30 days notice is required for voluntary resignation."},
        {"doc": DOCS["doc-8"], "chunk": 2, "text": "Remote work is allowed up to 3 days a week."},
        {"doc": DOCS["doc-8"], "chunk": 5, "text": "There is a $500 budget for home office equipment."},
        {"doc": DOCS["doc-9"], "chunk": 1, "text": "The SLA for sev-1 incidents is a 15 minute initial response time."},
        {"doc": DOCS["doc-10"], "chunk": 0, "text": "The primary contact for HR issues is the HR Business Partner assigned to your region."},
        {"doc": DOCS["doc-11"], "chunk": 6, "text": "The performance review schedule is biannual, in June and December."},
        {"doc": DOCS["doc-12"], "chunk": 9, "text": "Bonuses are completely discretionary and are not guaranteed."},
        {"doc": DOCS["doc-13"], "chunk": 20, "text": "The penalty for early termination of the contract is equal to 3 months fees."},
        {"doc": DOCS["doc-14"], "chunk": 7, "text": "Travel time outside of normal working hours is not compensated."},
        {"doc": DOCS["doc-15"], "chunk": 3, "text": "You can expense client dinners up to $100 per head."},
        {"doc": DOCS["doc-16"], "chunk": 11, "text": "The procedure for filing a grievance involves submitting a formal letter to Employee Relations."},
    ]
    
    texts = [c["text"] for c in mock_chunks]
    embeddings = embedder.embed_text(texts)
    
    records = []
    doc_records = []
    inserted_docs = set()
    
    for i, c in enumerate(mock_chunks):
        if c["doc"] not in inserted_docs:
            doc_records.append({
                "id": c["doc"],
                "box_id": box_id,
                "filename": f"mock-{c['doc']}.txt",
                "file_hash": f"hash-{c['doc']}",
                "mime_type": "text/plain",
                "status": "completed"
            })
            inserted_docs.add(c["doc"])
            
        records.append({
            "box_id": box_id,
            "document_id": c["doc"],
            "chunk_index": c["chunk"],
            "content": c["text"],
            "embedding": embeddings[i],
            "metadata": {"type": "mock"}
        })
        
    db.client.table("documents").insert(doc_records).execute()
    db.save_document_chunks(records)
    return mock_chunks, DOCS

async def run_benchmark(box_id: str):
    print("Initializing components...")
    db = _get_db_adapter()
    embedder = _get_embedder_adapter()
    llm = _get_llm_adapter()
    reranker = _get_reranker_adapter()
    
    # 1. Seed live data
    mock_chunks, DOCS = await seed_test_box(box_id, db, embedder)
    
    # Map the expected DOCS down in the benchmark data
    local_benchmark_data = []
    for item in BENCHMARK_DATA:
        old_doc_id = item["expected"][0][0]
        new_doc_id = DOCS.get(old_doc_id, old_doc_id)
        local_benchmark_data.append({
            "query": item["query"],
            "expected": [(new_doc_id, item["expected"][0][1])]
        })

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

    print(f"\nRunning benchmark on {len(local_benchmark_data)} queries...\n")
    
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
    
    for item in local_benchmark_data:
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
        
    print(f"\nCleaning up box '{box_id}'...")
    # Clean up mock documents
    doc_ids = set([c["expected"][0][0] for c in local_benchmark_data])
    for did in doc_ids:
        db.delete_document(did, box_id)
    print("Cleanup complete.")

if __name__ == "__main__":
    # Use the active Box ID from user logs
    TEST_BOX_ID = "a3727301-fd4b-418c-8b5f-4bf847b6cc43"
    
    # Run the async benchmark
    asyncio.run(run_benchmark(TEST_BOX_ID))
