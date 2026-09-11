-- ==========================================
-- Phase 1B: Box-Scoped Document Persistence
-- ==========================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- 1. Boxes (Phase 1A)
-- ==========================================
CREATE TABLE IF NOT EXISTS public.boxes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (char_length(btrim(name)) >= 1 AND char_length(btrim(name)) <= 100),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Unique index to prevent duplicate box names per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_boxes_user_name_lower ON public.boxes (user_id, lower(btrim(name)));

-- ==========================================
-- 2. Documents
-- ==========================================
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    box_id UUID NOT NULL REFERENCES public.boxes(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_document_hash_per_box UNIQUE (box_id, file_hash)
);

-- ==========================================
-- 3. Document Chunks
-- ==========================================
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1024), -- Validated runtime dimension for BAAI/bge-large-en-v1.5
    content_tsvector tsvector,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    page_start INTEGER,
    page_end INTEGER,
    section_title TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_chunk_per_doc UNIQUE (document_id, chunk_index)
);

-- Indexes for Document Chunks

CREATE INDEX IF NOT EXISTS idx_document_chunks_chunk_index ON public.document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_document_chunks_tsvector ON public.document_chunks USING GIN(content_tsvector);
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON public.document_chunks USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Trigger for auto-updating content_tsvector
CREATE OR REPLACE FUNCTION document_chunks_tsvector_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector := to_tsvector('english', NEW.content);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tsvector_update ON public.document_chunks;
CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE OF content
  ON public.document_chunks FOR EACH ROW EXECUTE FUNCTION document_chunks_tsvector_trigger();


-- ==========================================
-- Row Level Security (RLS) Policies
-- ==========================================

-- Enable RLS on the tables
ALTER TABLE public.boxes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

-- Boxes Policies
DROP POLICY IF EXISTS "boxes_select_policy" ON public.boxes;
CREATE POLICY "boxes_select_policy" ON public.boxes FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS "boxes_insert_policy" ON public.boxes;
CREATE POLICY "boxes_insert_policy" ON public.boxes FOR INSERT WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "boxes_update_policy" ON public.boxes;
CREATE POLICY "boxes_update_policy" ON public.boxes FOR UPDATE USING (user_id = auth.uid());

DROP POLICY IF EXISTS "boxes_delete_policy" ON public.boxes;
CREATE POLICY "boxes_delete_policy" ON public.boxes FOR DELETE USING (user_id = auth.uid());


-- Documents Policies
DROP POLICY IF EXISTS "documents_select_policy" ON public.documents;
CREATE POLICY "documents_select_policy" ON public.documents FOR SELECT USING (
    box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid())
);

DROP POLICY IF EXISTS "documents_insert_policy" ON public.documents;
CREATE POLICY "documents_insert_policy" ON public.documents FOR INSERT WITH CHECK (
    box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid())
);

DROP POLICY IF EXISTS "documents_update_policy" ON public.documents;
CREATE POLICY "documents_update_policy" ON public.documents FOR UPDATE USING (
    box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid())
);

DROP POLICY IF EXISTS "documents_delete_policy" ON public.documents;
CREATE POLICY "documents_delete_policy" ON public.documents FOR DELETE USING (
    box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid())
);

-- Document Chunks Policies
DROP POLICY IF EXISTS "document_chunks_select_policy" ON public.document_chunks;
CREATE POLICY "document_chunks_select_policy" ON public.document_chunks FOR SELECT USING (
    document_id IN (SELECT id FROM public.documents WHERE box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid()))
);

DROP POLICY IF EXISTS "document_chunks_insert_policy" ON public.document_chunks;
CREATE POLICY "document_chunks_insert_policy" ON public.document_chunks FOR INSERT WITH CHECK (
    document_id IN (SELECT id FROM public.documents WHERE box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid()))
);

DROP POLICY IF EXISTS "document_chunks_update_policy" ON public.document_chunks;
CREATE POLICY "document_chunks_update_policy" ON public.document_chunks FOR UPDATE USING (
    document_id IN (SELECT id FROM public.documents WHERE box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid()))
);

DROP POLICY IF EXISTS "document_chunks_delete_policy" ON public.document_chunks;
CREATE POLICY "document_chunks_delete_policy" ON public.document_chunks FOR DELETE USING (
    document_id IN (SELECT id FROM public.documents WHERE box_id IN (SELECT id FROM public.boxes WHERE user_id = auth.uid()))
);


-- ==========================================
-- RPC Functions
-- ==========================================

-- Hybrid Search RPC (Security Invoker)
-- By using SECURITY INVOKER, the query strictly obeys the caller's RLS policies (e.g., auth.uid()),
-- and because it's called using the service_role key by the backend, the backend MUST ensure match_box_id
-- ownership explicitly. We embed a strict join clause to guarantee chunks belong ONLY to the specified match_box_id.
CREATE OR REPLACE FUNCTION public.match_documents_hybrid_box(
    query_embedding vector(1024),
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
    chunk_index int,
    page_start int,
    page_end int,
    section_title text,
    metadata jsonb
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
          AND dc.content_tsvector @@ websearch_to_tsquery('english', query_text)
        ORDER BY lexical_score DESC
        LIMIT match_count * 2
    ),
    combined_search AS (
        SELECT 
            COALESCE(s.id, l.id) AS id,
            -- RRF formula constants: k=60
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
        dc.chunk_index,
        dc.page_start,
        dc.page_end,
        dc.section_title,
        dc.metadata
    FROM combined_search cs
    JOIN public.document_chunks dc ON dc.id = cs.id
    LEFT JOIN semantic_search s ON s.id = dc.id
    LEFT JOIN lexical_search l ON l.id = dc.id
    ORDER BY (cs.rrf_semantic_score + cs.rrf_lexical_score) DESC
    LIMIT match_count;
END;
$$;

-- By default, PostgreSQL grants EXECUTE on functions to PUBLIC.
-- Since this is intended for backend only (which authenticates as service_role), we restrict it.
REVOKE EXECUTE ON FUNCTION public.match_documents_hybrid_box(vector(1024), text, uuid, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_documents_hybrid_box(vector(1024), text, uuid, int) TO service_role;
