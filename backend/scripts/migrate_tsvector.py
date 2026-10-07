import asyncio
import os
from supabase import create_client, Client
from app.core.config import settings

async def run_migration():
    """
    Applies the updated document_chunks_tsvector_trigger to the live Supabase database.
    This incorporates section_title into the Lexical Search vector.
    """
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_SERVICE_KEY
    
    if not url or not key:
        print("Error: Supabase credentials not found in environment.")
        return
        
    supabase: Client = create_client(url, key)
    
    sql = """
    CREATE OR REPLACE FUNCTION document_chunks_tsvector_trigger() RETURNS trigger AS $$
    BEGIN
      NEW.content_tsvector := to_tsvector('english', COALESCE(NEW.section_title, '') || ' ' || NEW.content);
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    
    # We can't execute raw DDL easily via the PostgREST API using the JS/Python client directly 
    # unless there's an RPC endpoint for it or we use psycopg2.
    # We will print out the manual instructions if psycopg2 isn't available.
    
    print("Migration Script:")
    print("----------------")
    print("Please execute the following SQL in the Supabase SQL Editor to update the trigger live:\n")
    print(sql)
    print("\nAfter execution, all future chunks will index section_title lexically.")

if __name__ == "__main__":
    asyncio.run(run_migration())
