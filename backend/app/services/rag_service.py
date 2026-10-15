"""
قلب پروژه: پایپ‌لاین کامل RAG
مسئول: نفر ۲

مراحل طبق نیازمندی فایل نهایی:
۱) سوال کاربر Embed می‌شود
۲) نزدیک‌ترین chunkها از ChromaDB پیدا می‌شوند
۳) این chunkها + System Prompt کاربر + سوال با هم به مدل زبانی فرستاده می‌شوند
۴) پاسخ برمی‌گردد

این پایپ‌لاین باید هم برای «تست چت» (Playground) و هم برای «ویجت نهایی»
یکسان قابل استفاده باشد - به همین دلیل به‌صورت یک تابع مشترک نوشته شده
و در یک Endpoint واحد (routers/chat.py) فراخوانی می‌شود.
"""
from typing import List

from app.services import vector_store, embedding_service, llm_client


def answer_question(
    user_id: int,
    question: str,
    system_prompt: str,
    temperature: float,
    api_key: str,
    base_url: str,
    chat_model: str,
    embedding_model: str,
    top_k: int = 5,
) -> dict:
    """اجرای کامل پایپ‌لاین RAG برای یک سوال؛ خروجی شامل پاسخ و منابع استفاده‌شده"""

    # مرحله ۱: Embed کردن سوال
    query_embedding = embedding_service.get_embedding(
        text=question,
        api_key=api_key,
        base_url=base_url,
        model=embedding_model,
    )

    # مرحله ۲: جستجوی نزدیک‌ترین chunkها، فقط در Vector DB مخصوص همین کاربر
    search_results = vector_store.search(
        user_id=user_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )

    context_chunks: List[str] = [item["content"] for item in search_results]

    # مرحله ۳ و ۴: فراخوانی مدل زبانی با context + system prompt + سوال
    answer = llm_client.get_chat_completion(
        system_prompt=system_prompt,
        user_message=question,
        context_chunks=context_chunks,
        api_key=api_key,
        base_url=base_url,
        model=chat_model,
        temperature=temperature,
    )

    return {
        "answer": answer,
        "sources": search_results,
    }


def semantic_search_only(
    user_id: int,
    query: str,
    api_key: str,
    base_url: str,
    embedding_model: str,
    top_k: int = 5,
) -> List[dict]:
    """
    فقط جستجوی معنایی، بدون فرستادن به مدل زبانی.
    برای Endpoint جداگانه‌ی Semantic Search Playground (دیباگ).
    """
    query_embedding = embedding_service.get_embedding(
        text=query,
        api_key=api_key,
        base_url=base_url,
        model=embedding_model,
    )

    return vector_store.search(
        user_id=user_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )
