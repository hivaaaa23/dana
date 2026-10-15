"""
Endpoint چت RAG (قلب پروژه) و Semantic Search Playground
مسئول: نفر ۲

طبق نیازمندی، این Endpoint باید هم برای «تست چت» داخل پنل و هم برای
«ویجت نهایی» (نفر ۳) قابل استفاده باشد؛ به همین دلیل فقط یک Endpoint
مشترک ساخته شده (POST /api/chat) - هر دو مصرف‌کننده به آن وصل می‌شوند.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.settings import UserSettings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceChunk,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResult,
)
from app.services import rag_service, embedding_service, llm_client
from app.services.user_config import get_user_ai_config
from app.services import chat_log_service, injection_guard

router = APIRouter(prefix="/api/chat", tags=["Chat / RAG"])


_get_user_ai_config = get_user_ai_config


@router.post("", response_model=ChatResponse)
def chat_with_rag(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Endpoint اصلی چت RAG - قابل استفاده هم برای Playground داخلی و هم برای
    ویجت خروجی روی سایت‌های دیگر (به شرط ارسال هویت معتبر همان کاربر).
    """
    guard = injection_guard.check(payload.message)
    if injection_guard.should_block(guard):
        chat_log_service.record(db, current_user.id, "playground", ok=True, question=payload.message,
                                flagged=True, flag_reason=guard.reason)
        return ChatResponse(answer=injection_guard.REFUSAL_TEXT, sources=[])

    config = _get_user_ai_config(db, current_user)

    try:
        result = rag_service.answer_question(
            user_id=current_user.id,
            question=payload.message,
            system_prompt=config["system_prompt"],
            temperature=config["temperature"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            chat_model=config["chat_model"],
            embedding_model=config["embedding_model"],
            top_k=config["top_k"],
        )
    except RuntimeError as e:
        chat_log_service.record(db, current_user.id, "playground", ok=False, question=payload.message,
                                flagged=guard.flagged, flag_reason=guard.reason)
        raise HTTPException(status_code=502, detail=str(e))

    chat_log_service.record(
        db, current_user.id, "playground", ok=True, sources_count=len(result["sources"]),
        question=payload.message, answer=result["answer"],
        flagged=guard.flagged, flag_reason=guard.reason,
    )

    sources = [
        SourceChunk(
            content=s["content"],
            score=s["score"],
            document_id=s.get("document_id"),
            document_title=s.get("document_title"),
        )
        for s in result["sources"]
    ]

    return ChatResponse(answer=result["answer"], sources=sources)


@router.post("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search_playground(
    payload: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Endpoint جدا برای دیباگ: فقط نتیجه جستجوی معنایی (بدون فراخوانی مدل زبانی)
    به همراه Score شباهت برگردانده می‌شود.
    """
    config = _get_user_ai_config(db, current_user)

    try:
        raw_results = rag_service.semantic_search_only(
            user_id=current_user.id,
            query=payload.query,
            api_key=config["api_key"],
            base_url=config["base_url"],
            embedding_model=config["embedding_model"],
            top_k=payload.top_k,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    results = [
        SemanticSearchResult(
            content=r["content"],
            score=r["score"],
            document_id=r.get("document_id"),
            document_title=r.get("document_title"),
        )
        for r in raw_results
    ]

    return SemanticSearchResponse(query=payload.query, results=results)
