"""
مدل‌های Pydantic برای Endpoint چت RAG و Semantic Search Playground
مسئول: نفر ۲
"""
from typing import Optional, List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    # طبق نیازمندی، تاریخچه چت فقط در حافظه صفحه (سمت کلاینت) نگه داشته می‌شود
    # پس نیازی به ارسال/ذخیره تاریخچه در سرور نیست.
    session_id: Optional[str] = None


class SourceChunk(BaseModel):
    content: str
    score: float
    document_id: Optional[int] = None
    document_title: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = []


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class SemanticSearchResult(BaseModel):
    content: str
    score: float
    document_id: Optional[int] = None
    document_title: Optional[str] = None


class SemanticSearchResponse(BaseModel):
    query: str
    results: List[SemanticSearchResult]
