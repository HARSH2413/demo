-- ====================================================================
-- Migration: Switch from BAAI/bge-large-en-v1.5 (1024) to BAAI/bge-base-en-v1.5 (768)
-- ====================================================================

-- 1. Truncate old chunks (incompatible 1024-dimension vectors cannot be converted)
TRUNCATE TABLE public.document_chunks CASCADE;

-- 2. Drop existing HNSW index
DROP INDEX IF EXISTS public.idx_document_chunks_embedding;

-- 3. Alter embedding column to 768 dimensions
ALTER TABLE public.document_chunks 
  ALTER COLUMN embedding TYPE vector(768);

-- 4. Recreate HNSW index for vector(768)
CREATE INDEX idx_document_chunks_embedding 
  ON public.document_chunks 
  USING hnsw(embedding vector_cosine_ops) 
  WITH (m = 16, ef_construction = 64);

-- 5. Drop old 1024-dim RPC functions
DROP FUNCTION IF EXISTS public.match_documents_dense_box(vector(1024), uuid, int);
DROP FUNCTION IF EXISTS public.match_documents_hybrid_box(vector(1024), text, uuid, int);

-- 6. Recreate Dense Search RPC for vector(768)
CREATE OR REPLACE FUNCTION public.match_documents_dense_box(
    query_embedding vector(768),
    match_box_id uuid,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    embedding_score float,
    chunk_index int,
    page_start int,
    page_end int,
    section_title text,
    metadata jsonb,
    filename text
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> query_embedding) AS embedding_score,
        dc.chunk_index,
        dc.page_start,
        dc.page_end,
        dc.section_title,
        dc.metadata,
        d.filename
    FROM public.document_chunks dc
    JOIN public.documents d ON dc.document_id = d.id
    WHERE d.box_id = match_box_id
      AND d.status = 'completed'
    ORDER BY dc.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.match_documents_dense_box(vector(768), uuid, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_documents_dense_box(vector(768), uuid, int) TO service_role;

-- 7. Recreate Hybrid Search RPC for vector(768)
CREATE OR REPLACE FUNCTION public.match_documents_hybrid_box(
    query_embedding vector(768),
    query_text text,
    match_box_id uuid,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    embedding_score float,
    lexical_score float,
    rrf_score float,
    chunk_index int,
    page_start int,
    page_end int,
    section_title text,
    metadata jsonb,
    filename text
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    RETURN QUERY
    WITH semantic_search AS (
        SELECT 
            dc.id,
            1 - (dc.embedding <=> query_embedding) AS semantic_score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding ASC) AS semantic_rank
        FROM public.document_chunks dc
        JOIN public.documents d ON dc.document_id = d.id
        WHERE d.box_id = match_box_id
          AND d.status = 'completed'
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    lexical_search AS (
        SELECT 
            dc.id,
            ts_rank_cd(dc.content_tsvector, websearch_to_tsquery('english', query_text)) AS lexical_score,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.content_tsvector, websearch_to_tsquery('english', query_text)) DESC) AS lexical_rank
        FROM public.document_chunks dc
        JOIN public.documents d ON dc.document_id = d.id
        WHERE d.box_id = match_box_id
          AND d.status = 'completed'
          AND dc.content_tsvector @@ websearch_to_tsquery('english', query_text)
        ORDER BY lexical_score DESC
        LIMIT match_count * 2
    ),
    combined_search AS (
        SELECT 
            COALESCE(s.id, l.id) AS id,
            COALESCE(1.0 / (60 + s.semantic_rank), 0.0) AS rrf_semantic_score,
            COALESCE(1.0 / (60 + l.lexical_rank), 0.0) AS rrf_lexical_score
        FROM semantic_search s
        FULL OUTER JOIN lexical_search l ON s.id = l.id
    )
    SELECT 
        dc.id,
        dc.document_id,
        dc.content,
        s.semantic_score AS embedding_score,
        l.lexical_score AS lexical_score,
        (cs.rrf_semantic_score + cs.rrf_lexical_score) AS rrf_score,
        dc.chunk_index,
        dc.page_start,
        dc.page_end,
        dc.section_title,
        dc.metadata,
        d.filename
    FROM combined_search cs
    JOIN public.document_chunks dc ON dc.id = cs.id
    JOIN public.documents d ON d.id = dc.document_id
    LEFT JOIN semantic_search s ON s.id = dc.id
    LEFT JOIN lexical_search l ON l.id = dc.id
    ORDER BY rrf_score DESC
    LIMIT match_count;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.match_documents_hybrid_box(vector(768), text, uuid, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_documents_hybrid_box(vector(768), text, uuid, int) TO service_role;
