-- ============================================================
-- ActionRAG Phase 2: RRF Hybrid Search + Performance Indexes
-- Run this ENTIRE script in your Supabase SQL Editor (one shot)
-- ============================================================

-- 1. Add pre-computed tsvector column for full-text search
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_tsvector tsvector;

-- 2. Populate tsvector for ALL existing rows
UPDATE documents SET content_tsvector = to_tsvector('english', content)
WHERE content_tsvector IS NULL;

-- 3. Auto-update tsvector on insert/update (trigger)
CREATE OR REPLACE FUNCTION documents_tsvector_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector := to_tsvector('english', NEW.content);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tsvector_update ON documents;
CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE OF content
  ON documents FOR EACH ROW EXECUTE FUNCTION documents_tsvector_trigger();

-- 4. GIN index for full-text search (100x faster keyword search)
CREATE INDEX IF NOT EXISTS idx_documents_tsvector ON documents USING GIN(content_tsvector);

-- 5. HNSW index for vector search (10-50x faster similarity search)
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents
  USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- 6. Tenant filtering index (speeds up WHERE tenant_id = X)
CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id);

-- 7. Replace hybrid search with Reciprocal Rank Fusion (RRF)
CREATE OR REPLACE FUNCTION match_documents_hybrid(
  query_embedding vector,
  query_text text,
  match_tenant_id text,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  filename text,
  content text,
  similarity float
)
LANGUAGE plpgsql
AS $$
DECLARE
  rrf_k int := 60;  -- Standard RRF smoothing constant
BEGIN
  RETURN QUERY
  WITH semantic_search AS (
    -- Vector similarity search (uses HNSW index)
    SELECT
      d.id,
      ROW_NUMBER() OVER (ORDER BY d.embedding <=> query_embedding) AS rank_ix
    FROM documents d
    WHERE d.tenant_id::text = match_tenant_id
    ORDER BY d.embedding <=> query_embedding
    LIMIT LEAST(match_count * 4, 100)
  ),
  keyword_search AS (
    -- Full-text search with ranking (uses GIN index + pre-computed tsvector)
    SELECT
      d.id,
      ROW_NUMBER() OVER (
        ORDER BY ts_rank_cd(d.content_tsvector, websearch_to_tsquery('english', query_text)) DESC
      ) AS rank_ix
    FROM documents d
    WHERE d.tenant_id::text = match_tenant_id
      AND d.content_tsvector @@ websearch_to_tsquery('english', query_text)
    LIMIT LEAST(match_count * 4, 100)
  )
  SELECT
    d.id,
    d.filename::text,
    d.content::text,
    -- RRF: 1/(k+rank) — puts both search signals on the SAME scale
    -- Documents found by BOTH methods get the highest combined scores
    (
      COALESCE(1.0 / (rrf_k + ss.rank_ix), 0.0) +
      COALESCE(1.0 / (rrf_k + ks.rank_ix), 0.0)
    )::float AS similarity
  FROM documents d
  LEFT JOIN semantic_search ss ON d.id = ss.id
  LEFT JOIN keyword_search ks ON d.id = ks.id
  WHERE ss.id IS NOT NULL OR ks.id IS NOT NULL
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
