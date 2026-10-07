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
from app.core.auth import get_current_user, verify_box_access, UserContext
import os
from groq import Groq

def check_prompt_injection(prompt: str) -> bool:
    """Returns True if the prompt is detected as a jailbreak or injection."""
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        return False
        
    try:
        client = Groq(api_key=groq_api_key)
        completion = client.chat.completions.create(
            model="meta-llama/llama-prompt-guard-2-86m",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        content = completion.choices[0].message.content.strip()
        # Prompt Guard 2 returns a probability float
        score = float(content)
        if score > 0.5:
            logger.warning(f"Prompt injection detected | score={score:.4f}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Prompt guard check failed, bypassing: {e}")
        return False

router = APIRouter(prefix="/api/v1/chat", tags=["Enterprise Q&A"])


# ── API Contracts ──

class SessionRequest(BaseModel):
    box_id: str
    title: Optional[str] = "New Conversation"


class ChatRequest(BaseModel):
    question: str
    box_id: str
    session_id: str


class RenameSessionRequest(BaseModel):
    title: str


class Citation(BaseModel):
    evidence_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: str
    chunk_index: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_title: Optional[str] = None
    content: str
    embedding_score: Optional[float] = None
    lexical_score: Optional[float] = None
    rrf_score: Optional[float] = None
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
    box_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_box_access(box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this box.")
    try:
        return {"status": "success", "sessions": chat_service.db.list_chat_sessions(box_id)}
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
    if not verify_box_access(request.box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this box.")
    try:
        session_id = chat_service.db.create_chat_session(
            box_id=request.box_id,
            title=request.title,
        )
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        logger.exception(f"Chat session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to create the chat session.")


@router.get("/sessions/{session_id}")
async def get_chat_history(
    session_id: str,
    box_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    """Allows the frontend to load past messages when a user clicks an old chat."""
    if not verify_box_access(box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this box.")
    try:
        if not chat_service.db.session_belongs_to_box(session_id, box_id):
            raise HTTPException(status_code=404, detail="Chat session not found.")
        history = chat_service.db.get_chat_history(session_id=session_id, box_id=box_id)
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
    box_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_box_access(box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this box.")
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="A conversation title is required.")
    if not chat_service.db.rename_chat_session(session_id, box_id, title[:120]):
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"status": "success", "title": title[:120]}


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    box_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_box_access(box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this box.")
    try:
        if not chat_service.db.delete_chat_session(session_id, box_id):
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
    if not verify_box_access(chat_request.box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this box.")
    try:
        if check_prompt_injection(chat_request.question):
            raise HTTPException(status_code=400, detail="Request blocked by Prompt Guard.")
            
        if not chat_service.db.session_belongs_to_box(chat_request.session_id, chat_request.box_id):
            raise HTTPException(status_code=404, detail="Chat session not found.")
        response = chat_service.ask_question(
            question=chat_request.question,
            box_id=chat_request.box_id,
            session_id=chat_request.session_id,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to process the question.")
