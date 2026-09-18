from app.infrastructure.reranker_adapter import FastEmbedRerankerAdapter

def test_reranker():
    reranker = FastEmbedRerankerAdapter()
    docs = [{"content": "hello world"}, {"content": "the quick brown fox"}]
    res = reranker.rerank("fox", docs)
    print("Result:")
    for d in res:
        print(d["content"], d["rerank_score"])

if __name__ == "__main__":
    test_reranker()
