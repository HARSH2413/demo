-- ==========================================
-- Phase 1C: Box Domain Schema Update
-- ==========================================

-- Add the domain column to the boxes table with a CHECK constraint
-- to ensure it only contains valid vocabulary terms.
ALTER TABLE public.boxes 
ADD COLUMN IF NOT EXISTS domain TEXT 
CHECK (domain IN (
    'finance', 
    'legal', 
    'human_resources', 
    'engineering', 
    'sales', 
    'marketing', 
    'operations', 
    'compliance', 
    'general'
));
