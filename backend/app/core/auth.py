from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel
from typing import Optional
from cachetools import TTLCache
from app.core.config import settings
from app.core.logger import logger
from app.core.dependencies import _get_db_adapter

security = HTTPBearer()

class UserContext(BaseModel):
    user_id: str
    email: str
    role: Optional[str] = None

# Cache valid tokens for 5 minutes to avoid hitting Supabase API repeatedly
_token_cache = TTLCache(maxsize=1000, ttl=300)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserContext:
    """Verifies the Supabase JWT token and extracts user information securely using the Supabase SDK."""
    token = credentials.credentials
    
    if token in _token_cache:
        return _token_cache[token]
        
    try:
        db = _get_db_adapter()
        # This calls Supabase's auth service, verifying the token securely via Supabase's own API
        # This automatically handles asymmetric keys (ES256, RS256) and symmetric keys (HS256)
        user_resp = db.client.auth.get_user(token)
        
        if not user_resp or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        user = user_resp.user
        ctx = UserContext(
            user_id=user.id,
            email=user.email,
            role=user.role
        )
        
        _token_cache[token] = ctx
        return ctx
    except Exception as e:
        error_name = type(e).__name__
        if error_name == "AuthApiError" or "invalid" in str(e).lower() or "expired" in str(e).lower():
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        logger.error(f"Unexpected error validating token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def verify_box_access(box_id: str, user_id: str) -> dict:
    """
    Checks if a user has access to a box and returns the box object.
    Raises HTTPException if not found or unauthorized.
    """
    db = _get_db_adapter()
    try:
        result = db.client.table("boxes").select("*").eq("id", box_id).eq("user_id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Box not found or unauthorized")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking box access: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
