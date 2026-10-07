-- ==========================================
-- Phase 1E: Dense-Only Retrieval RPC
-- ==========================================

DROP FUNCTION IF EXISTS public.match_documents_dense_box(vector(1024), uuid, int);

CREATE OR REPLACE FUNCTION public.match_documents_dense_box(
    query_embedding vector(1024),
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

REVOKE EXECUTE ON FUNCTION public.match_documents_dense_box(vector(1024), uuid, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_documents_dense_box(vector(1024), uuid, int) TO service_role;
