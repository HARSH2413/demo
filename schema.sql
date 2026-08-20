-- Reconstructed Database Schema for Action.ai (Supabase/PostgreSQL)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- 1. Workspaces (Tenants)
-- ==========================================
CREATE TABLE IF NOT EXISTS public.workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- 2. Workspace Members
-- ==========================================
CREATE TABLE IF NOT EXISTS public.workspace_members (
    workspace_id UUID REFERENCES public.workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);

-- ==========================================
-- 3. Documents
-- ==========================================
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES public.workspaces(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content TEXT NOT NULL,
    file_hash TEXT,
    embedding vector(384), -- Assuming 384 dimensions for FastEmbed (BGE), change if different
    content_tsvector tsvector,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for Documents table
CREATE INDEX IF NOT EXISTS idx_documents_tsvector ON documents USING GIN(content_tsvector);
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING hnsw(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id);

-- Trigger for auto-updating content_tsvector
CREATE OR REPLACE FUNCTION documents_tsvector_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsvector := to_tsvector('english', NEW.content);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tsvector_update ON documents;
CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE OF content
  ON documents FOR EACH ROW EXECUTE FUNCTION documents_tsvector_trigger();

-- ==========================================
-- 4. Chat Sessions
-- ==========================================
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES public.workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- 5. Chat Messages
-- ==========================================
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- Row Level Security (RLS) Policies
-- ==========================================

-- Workspaces RLS
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view workspaces they are members of" ON public.workspaces;
DROP POLICY IF EXISTS "Owners can insert workspaces" ON public.workspaces;
DROP POLICY IF EXISTS "Select workspace" ON public.workspaces;
DROP POLICY IF EXISTS "Insert workspace" ON public.workspaces;

CREATE POLICY "Select workspace" ON public.workspaces
FOR SELECT USING (
  owner_id = auth.uid() OR
  id IN (SELECT workspace_id FROM public.workspace_members WHERE user_id = auth.uid())
);

CREATE POLICY "Insert workspace" ON public.workspaces
FOR INSERT WITH CHECK (owner_id = auth.uid());

-- Workspace Members RLS
ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view members of their workspaces" ON public.workspace_members;
DROP POLICY IF EXISTS "Users can insert themselves as owners" ON public.workspace_members;
DROP POLICY IF EXISTS "Select workspace members" ON public.workspace_members;
DROP POLICY IF EXISTS "Insert workspace members" ON public.workspace_members;

CREATE POLICY "Select workspace members" ON public.workspace_members
FOR SELECT USING (
  user_id = auth.uid()
);

CREATE POLICY "Insert workspace members" ON public.workspace_members
FOR INSERT WITH CHECK (user_id = auth.uid());

-- (Additional RLS policies should similarly be added for documents, chat_sessions, and chat_messages filtering by tenant_id)
