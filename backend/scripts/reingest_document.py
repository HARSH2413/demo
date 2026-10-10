import os
import sys
import uuid
import logging
from app.core.config import settings
from app.infrastructure.supabase_adapter import SupabaseAdapter
from app.infrastructure.fastembed_adapter import FastEmbedAdapter
from app.infrastructure.bm25s_adapter import BM25SAdapter
from app.services.ingestion_service import IngestionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reingest_document(file_path: str, document_id: str):
    """
    Re-ingests a single document by its ID.
    Inserts new chunks first. Only upon complete success, deletes old chunks.
    Reuses orphan cleanup from ingestion_service.
    """
    db = SupabaseAdapter()
    embedder = FastEmbedAdapter()
    bm25_store = BM25SAdapter()
    
    # Initialize ingestion service
    service = IngestionService(db=db, lexical_store=bm25_store, embedder=embedder)
    
    # Fetch document metadata
    response = db.client.table("documents").select("*").eq("id", document_id).execute()
    if not response.data:
        logger.error(f"Document with ID {document_id} not found.")
        return
        
    doc = response.data[0]
    box_id = doc["box_id"]
    filename = doc["filename"]
    # file_path is passed as an argument
    if not os.path.exists(file_path):
        logger.error(f"File not found on disk: {file_path}")
        return
        
    file_hash = service._calculate_hash(file_path)
        
    # Get old chunk count
    old_chunks_resp = db.client.table("document_chunks").select("id").eq("document_id", document_id).execute()
    old_ids = [c["id"] for c in old_chunks_resp.data]
    old_count = len(old_ids)
        
    logger.info(f"Re-ingesting document {document_id} ({filename})")
    
    # 1. Verify file hash
    if doc.get("file_hash") != file_hash:
        logger.error(f"Hash mismatch! Document has {doc.get('file_hash')}, provided file has {file_hash}.")
        logger.error("Aborting to prevent corrupting the document record with mismatched contents.")
        sys.exit(1)
        
    logger.info(f"Current chunk count: {old_count}")
    
    # Insert new chunks under a shadow ID to prevent mixing and satisfy FK
    shadow_id = str(uuid.uuid4())
    logger.info(f"Using shadow ID for new chunks: {shadow_id}")
    
    try:
        # Create shadow document to satisfy FK constraint.
        # We use a status like "shadow" so it won't appear in UI listings or BM25 processing.
        db.client.table("documents").insert({
            "id": shadow_id,
            "box_id": box_id,
            "filename": f"SHADOW_{filename}",
            "file_hash": f"shadow_{file_hash}_{uuid.uuid4().hex[:8]}", # prevent unique constraint collision on file_hash
            "status": "shadow"
        }).execute()
        
        # Ingestion pipeline using shadow ID
        service.process_file_background(file_path, filename, file_hash, box_id, shadow_id)
        
        # Verify success
        new_chunks_resp = db.client.table("document_chunks").select("id", count="exact").eq("document_id", shadow_id).execute()
        new_count = new_chunks_resp.count if new_chunks_resp.count else 0
        logger.info(f"Successfully generated {new_count} new chunks.")
        
        # Atomically swap: Ideally done via an RPC/SQL transaction (see migrations/20261008_swap_chunks.sql).
        # Fallback script order if RPC not available:
        # 1. Collect old IDs (already done).
        # 2. Repoint shadow chunks to real document. (At this exact moment, both old and new chunks exist for the doc).
        # 3. Delete old chunk IDs.
        logger.info("Promoting shadow chunks to real document ID...")
        db.client.table("document_chunks").update({"document_id": document_id}).eq("document_id", shadow_id).execute()
        
        if old_ids:
            logger.info("Deleting old chunks...")
            for i in range(0, len(old_ids), 100):
                batch_ids = old_ids[i:i+100]
                db.client.table("document_chunks").delete().in_("id", batch_ids).execute()
        
        # Rebuild BM25 index because chunks have changed
        logger.info("Rebuilding BM25 index for the box...")
        bm25_store.invalidate_box(box_id)
        bm25_store.ensure_box_index(box_id)
        
        # Ensure status is completed on real doc
        db.update_document_status(document_id, "completed")
        logger.info("Re-ingestion complete!")
        
    except Exception as e:
        logger.error(f"Re-ingestion failed: {e}")
        logger.info(f"Old chunks ({old_count}) were preserved.")
    finally:
        # ALWAYS cleanup shadow doc if it exists
        logger.info("Cleaning up shadow document record...")
        try:
            db.client.table("documents").delete().eq("id", shadow_id).execute()
        except:
            pass
    
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reingest_document.py <local_file_path> <document_id>")
        sys.exit(1)
        
    reingest_document(sys.argv[1], sys.argv[2])
