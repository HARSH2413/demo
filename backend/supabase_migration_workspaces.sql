-- supabase_migration_workspaces.sql
-- Create workspaces and multi-tenant isolation structure.

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create Workspaces Table
CREATE TABLE IF NOT EXISTS public.workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Create Workspace Members Table
CREATE TABLE IF NOT EXISTS public.workspace_members (
    workspace_id UUID REFERENCES public.workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);

-- 3. Update Existing Tables (Optional but recommended to link tenant_id to workspace)
-- We assume tenant_id in 'documents' and 'chat_history' maps to workspaces.id.
-- Since the user might wipe the DB, we just ensure the foreign keys are defined if possible.
-- If they want to keep the old hardcoded ID, they can manually insert a workspace with that ID.

-- ALTER TABLE public.documents
-- ADD CONSTRAINT fk_workspace
-- FOREIGN KEY (tenant_id)
-- REFERENCES public.workspaces(id)
-- ON DELETE CASCADE;

-- 4. Set up Row Level Security (RLS)
-- This ensures users can only see their own workspaces and documents within them.

-- Workspaces
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

-- Workspace Members
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

-- Note: We also need to secure the `documents` and `chat_history` tables similarly.
-- We will assume they use `tenant_id` as the workspace_id.
