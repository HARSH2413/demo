"""
Chat API — async endpoint with config-driven rate limiting.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.services.chat_service import ChatService
from app.core.dependencies import get_chat_service
from app.core.rate_limiter import limiter
from app.core.config import settings
from app.core.logger import logger
from app.core.auth import get_current_user, verify_workspace_access, UserContext

router = APIRouter(prefix="/api/v1/chat", tags=["Enterprise Q&A"])


# ── API Contracts ──

class SessionRequest(BaseModel):
    tenant_id: str
    title: Optional[str] = "New Conversation"


class ChatRequest(BaseModel):
    question: str
    tenant_id: str
    session_id: str


class RenameSessionRequest(BaseModel):
    title: str


class Citation(BaseModel):
    filename: str
    content: str
    similarity: float = 0.0
    rerank_score: Optional[float] = None


class EnhancedChatResponse(BaseModel):
    answer: str
    key_takeaways: list[str] = []
    related_questions: list[str] = []
    citations: list[Citation] = []
    session_id: str
    confidence: str


# ── Endpoints ──

@router.get("/sessions")
async def list_chat_sessions(
    tenant_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    try:
        return {"status": "success", "sessions": chat_service.db.list_chat_sessions(tenant_id)}
    except Exception as e:
        logger.exception(f"Chat session list failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to load chat sessions.")


@router.post("/sessions")
async def create_new_chat_session(
    request: SessionRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    """Creates a blank chat room and returns the session_id to the frontend."""
    if not verify_workspace_access(request.tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    try:
        session_id = chat_service.db.create_chat_session(
            tenant_id=request.tenant_id,
            title=request.title,
        )
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        logger.exception(f"Chat session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to create the chat session.")


@router.get("/sessions/{session_id}")
async def get_chat_history(
    session_id: str,
    tenant_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    """Allows the frontend to load past messages when a user clicks an old chat."""
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    try:
        if not chat_service.db.session_belongs_to_tenant(session_id, tenant_id):
            raise HTTPException(status_code=404, detail="Chat session not found.")
        history = chat_service.db.get_chat_history(session_id=session_id, tenant_id=tenant_id)
        return {"status": "success", "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat history lookup failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to load chat history.")


@router.patch("/sessions/{session_id}")
async def rename_chat_session(
    session_id: str,
    request: RenameSessionRequest,
    tenant_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="A conversation title is required.")
    if not chat_service.db.rename_chat_session(session_id, tenant_id, title[:120]):
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"status": "success", "title": title[:120]}


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    tenant_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    try:
        if not chat_service.db.delete_chat_session(session_id, tenant_id):
            raise HTTPException(status_code=404, detail="Chat session not found.")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat session deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to delete the chat session.")


@router.post("/", response_model=EnhancedChatResponse)
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat_with_documents(
    request: Request,
    chat_request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    """The main chat engine. Automatically reads history and saves new messages."""
    if not verify_workspace_access(chat_request.tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    try:
        if not chat_service.db.session_belongs_to_tenant(chat_request.session_id, chat_request.tenant_id):
            raise HTTPException(status_code=404, detail="Chat session not found.")
        response = chat_service.ask_question(
            question=chat_request.question,
            tenant_id=chat_request.tenant_id,
            session_id=chat_request.session_id,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to process the question.")
