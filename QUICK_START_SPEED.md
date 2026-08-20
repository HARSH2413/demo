# QUICK START - Reduce Latency in 10 Minutes

**Current problem:** Answers take 10-12 seconds
**Target after these steps:** 2-4 seconds (60% faster)

---

## Step 1: Edit .env (2 min)

Copy `.env.template` to `.env` and update:

```bash
cp .env.template .env
# Then edit .env with your keys
```

**Key changes for speed:**

```env
# DISABLE slow features
ENABLE_HYDE=false                    # Saves 1-2s
ENABLE_MULTI_QUERY=false             # Saves 1-2s
ENABLE_KEY_TAKEAWAYS=false           # Saves 0.5s
ENABLE_RELATED_QUESTIONS=false       # Saves 0.5s
ENABLE_NEIGHBOR_CONTEXT=false        # Saves 0.2s

# REDUCE retrieval overhead
RETRIEVAL_TOP_K=20                   # was 40 (50% reduction)
RERANKER_TOP_K=5                     # was 8

# STRICTER filtering
MIN_RELEVANCE_SCORE=0.5              # was 0.3
```

👉 **Just editing .env cuts response time by 50%**

---

## Step 2: Test the "fast" endpoint (3 min)

Add this to `backend/app/main.py` router mounting:

```python
from app.api.chat_streaming import router as chat_streaming_router

app.include_router(chat_streaming_router)
```

Now test:
```bash
curl -X POST http://localhost:8000/api/v1/chat/fast \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is X?",
    "tenant_id": "test",
    "session_id": "sess123"
  }'
```

**Expected:** 2-4 seconds ✓

---

## Step 3: Enable streaming (3 min)

In `frontend/src/app/page.tsx`:

```typescript
import { StreamingChat } from '@/components/StreamingChat';

export default function Home() {
  return (
    <div className="p-4">
      <h1>ActionRAG - Fast Chat</h1>
      <StreamingChat sessionId="user-123" tenantId="tenant-123" />
    </div>
  );
}
```

**Expected:** User sees first words in 1-2 seconds instead of waiting 8-12 seconds

---

## Step 4: Add caching (2 min)

Update `backend/app/core/dependencies.py`:

```python
from app.core.cache import EmbeddingCache, QueryResultCache

embedding_cache = EmbeddingCache()
query_cache = QueryResultCache()

@lru_cache()
def get_embedding_cache() -> EmbeddingCache:
    return embedding_cache

@lru_cache()
def get_query_cache() -> QueryResultCache:
    return query_cache
```

Update `backend/app/services/chat_service.py` to use cache:

```python
class ChatService:
    def __init__(self, ..., embedding_cache: EmbeddingCache = None):
        self.embedding_cache = embedding_cache or EmbeddingCache()

    def _multi_query_search(self, queries, original_query, tenant_id):
        for query in queries:
            # Check cache first
            cached = self.embedding_cache.get_embedding(query)
            if cached:
                query_vector = cached
                logger.info(f"✓ Cache hit for embedding")
            else:
                query_vector = self.embedder.embed_text([query])[0]
                self.embedding_cache.set_embedding(query, query_vector)
            # ... rest of code
```

**Expected:** Repeated questions answer in 0.5 seconds (cache hit)

---

## Step 5: Check Supabase indexes (1 min)

Run this in Supabase SQL editor:

```sql
-- Check HNSW index exists
SELECT * FROM pg_indexes WHERE indexname LIKE '%hnsw%';

-- If not, create it
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw
ON documents USING hnsw (embedding vector_cosine_ops);

-- Check full-text index
SELECT * FROM pg_indexes WHERE indexname LIKE '%gin%';

-- If not, create it
CREATE INDEX IF NOT EXISTS documents_tsvector_gin
ON documents USING GIN (content_tsvector);

-- Check indexes exist
SELECT schemaname, tablename, indexname, indextype
FROM pg_indexes
WHERE tablename = 'documents';
```

**Expected output:**
```
documents_embedding_hnsw    | hnsw
documents_tsvector_gin      | gin
documents_pkey              | btree
```

---

## SPEED COMPARISON

| Metric | Before | After (Quick Wins) | After (Full) |
|--------|--------|-------------------|--------------|
| Response Time | 10-12s | 2-4s ✓ | 1-2s (streaming) |
| Improvement | — | 60% faster | 80-90% faster |
| Features | All | Minimal | Streaming |
| Cost | $0 | $0 | $0 (free tier) |

---

## DEPLOYMENT (Free Tier - Optional)

### Frontend → Vercel (3 min)

```bash
cd frontend
npm install -g vercel
vercel login
vercel --prod
```

Result: `https://your-project.vercel.app` 🌍

### Backend → Railway (5 min)

```bash
cd backend
npm install -g @railway/cli
railway login
railway init
railway env add SUPABASE_URL "..."
railway env add SUPABASE_SERVICE_KEY "..."
railway env add GROQ_API_KEY "..."
railway up
```

Result: `https://your-project-railway.app` ⚡

### Keep Backend Warm (Free)

Backend sleeps after 30 min idle. Add a cron job at **EasyCron.com**:
- URL: `https://your-project-railway.app/api/v1/chat/health`
- Interval: Every 15 minutes
- Cost: Free

---

## API ENDPOINTS

### Fast (Best for free tier)
```bash
POST /api/v1/chat/fast
# Features disabled, 2-4 second response
```

### Streaming (See tokens in real-time)
```bash
POST /api/v1/chat/stream
# SSE streaming, 1-2s to first token
```

### Standard (Original)
```bash
POST /api/v1/chat
# Full features if enabled in .env
```

---

## VERIFY SPEED IMPROVEMENTS

```bash
# Test response time
time curl -X POST http://localhost:8000/api/v1/chat/fast \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the company policy?", "tenant_id": "test", "session_id": "test"}'

# Should print: "real 0m2.4s" or similar (2-4 seconds) ✓
```

---

## COMMON ISSUES

### Q: Still slow (>5 seconds)?
A: Check:
1. Is Supabase in same region? (Lower latency)
2. Are RETRIEVAL_TOP_K and RERANKER_TOP_K reduced?
3. Are features disabled in .env?
4. Is Groq API responding fast? (test: `curl https://api.groq.com/health`)

### Q: Streaming not working?
A: Frontend needs to consume SSE:
```typescript
const response = await fetch('/api/v1/chat/stream');
const reader = response.body.getReader();
// Process chunks...
```

### Q: How to re-enable features later?
A: Just set in .env:
```env
ENABLE_HYDE=true
ENABLE_MULTI_QUERY=true
ENABLE_KEY_TAKEAWAYS=true
ENABLE_RELATED_QUESTIONS=true
```
Response time will be 5-8 seconds instead of 2-4, but more comprehensive.

---

## MONITORING

Add logging to see where time is spent:

```python
import time

@router.post("/api/v1/chat/fast")
async def chat_fast(request: ChatFastRequest):
    t0 = time.time()

    t_search = t0
    docs = service.search(...)
    print(f"Search: {time.time() - t_search:.2f}s")

    t_rerank = time.time()
    reranked = reranker.rerank(...)
    print(f"Rerank: {time.time() - t_rerank:.2f}s")

    t_llm = time.time()
    answer = llm.answer(...)
    print(f"LLM: {time.time() - t_llm:.2f}s")

    print(f"TOTAL: {time.time() - t0:.2f}s")

    return result
```

This shows which component is slowest.

---

## NEXT STEPS

After speed improvements:

1. **Monitor real-world performance** - Check Vercel/Railway logs
2. **Collect user feedback** - Is 2-4s acceptable?
3. **Consider paid upgrades if needed:**
   - Railway Pro: $7/mo (+4GB RAM)
   - Supabase Pro: $25/mo (+3GB storage)
   - This could reduce response time to 1-2s

---

## SUMMARY

✅ Edit `.env` - 50% faster
✅ Test `/fast` endpoint - 2-4 second response
✅ Enable streaming - 1-2s perceived speed (first tokens shown immediately)
✅ Add caching - 0.5s for repeated questions
✅ Deploy to Vercel/Railway - Free, global

**Total setup time: ~15 minutes**
**Performance improvement: 60-80%**
**Cost: $0/month** 🎉
