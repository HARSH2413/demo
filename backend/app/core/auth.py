from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.logger import logger
from app.core.dependencies import _get_db_adapter

security = HTTPBearer()

class UserContext(BaseModel):
    user_id: str
    email: str
    role: Optional[str] = None

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserContext:
    """Verifies the Supabase JWT token and extracts user information."""
    token = credentials.credentials
    try:
        # Supabase uses HS256 algorithm by default for its JWTs
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        return UserContext(
            user_id=payload.get("sub"),
            email=payload.get("email", ""),
            role=payload.get("role")
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_workspace_access(tenant_id: str, user_id: str) -> bool:
    """
    Checks if a user has access to a workspace via database lookup.
    """
    db = _get_db_adapter()
    try:
        # Since SupabaseAdapter doesn't have this method yet, we use the underlying client directly
        result = db.client.table("workspace_members").select("*").eq("workspace_id", tenant_id).eq("user_id", user_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Error checking workspace access: {e}")
        return False
