-- Migration: Swap Document Chunks Atomically
-- Creates an RPC function to atomically delete old chunks and repoint new chunks to the real document ID.

CREATE OR REPLACE FUNCTION swap_document_chunks(old_doc_id UUID, new_doc_id UUID)
RETURNS void AS $$
BEGIN
    -- 1. Delete all chunks belonging to the old document
    DELETE FROM document_chunks
    WHERE document_id = old_doc_id;

    -- 2. Repoint all chunks from the shadow document to the real document
    UPDATE document_chunks
    SET document_id = old_doc_id
    WHERE document_id = new_doc_id;
END;
$$ LANGUAGE plpgsql;
