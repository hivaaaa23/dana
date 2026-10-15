"""
لایه اتصال به ChromaDB (Vector Store) + عملیات Chunk کردن متن
مسئول: نفر ۲

نکته جداسازی داده (سطح Vector DB):
برای هر کاربر یک Collection جداگانه در ChromaDB ساخته می‌شود تا هیچ داده‌ای
بین کاربران به اشتراک گذاشته نشود (جداسازی داده، این‌بار در سطح Vector DB).
"""
import re
import uuid
from typing import List, Optional

import chromadb

from app.config import settings as app_settings

# ---------------------------------------------------------------------------
# راه‌اندازی کلاینت ChromaDB (Embedded / Persistent - بدون نیاز به سرور جدا)
# ---------------------------------------------------------------------------
_chroma_client = chromadb.PersistentClient(
    path=getattr(app_settings, "CHROMA_PERSIST_DIR", "./chroma_db"),
)


def _collection_name_for_user(user_id: int) -> str:
    """نام یکتای Collection برای هر کاربر"""
    return f"user_{user_id}_kb"


def get_user_collection(user_id: int):
    """Collection مخصوص یک کاربر را برمی‌گرداند (در صورت نبود، می‌سازد)"""
    return _chroma_client.get_or_create_collection(
        name=_collection_name_for_user(user_id),
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Chunk کردن متن سند
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    متن را بر اساس تعداد کلمه به تکه‌های کوچک‌تر تقسیم می‌کند.
    overlap باعث می‌شود context بین تکه‌های پیاپی قطع نشود.
    """
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split(" ")

    if not words or words == [""]:
        return []

    step = chunk_size - overlap
    if step <= 0:
        # جلوگیری از حلقه بی‌نهایت در صورت تنظیمات نامعتبر (overlap >= chunk_size)
        step = chunk_size

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


# ---------------------------------------------------------------------------
# افزودن / حذف / جستجوی سند در Vector DB
# ---------------------------------------------------------------------------
def add_document(
    user_id: int,
    document_id: int,
    chunks: List[str],
    embeddings: List[List[float]],
    document_title: Optional[str] = None,
) -> List[str]:
    """
    بردارهای embedding شده هر chunk را همراه با متادیتا در Collection کاربر ذخیره می‌کند.
    خروجی: لیست شناسه‌های یکتای ذخیره‌شده در Chroma (برای امکان حذف بعدی).
    """
    if len(chunks) != len(embeddings):
        raise ValueError("تعداد chunkها و embeddingها باید برابر باشد")

    if not chunks:
        return []

    collection = get_user_collection(user_id)

    chunk_ids = [f"doc{document_id}_chunk{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
    metadatas = [
        {"document_id": document_id, "document_title": document_title or "", "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return chunk_ids


def delete_document(user_id: int, document_id: int) -> None:
    """حذف تمام chunkهای مربوط به یک سند خاص از Vector DB کاربر"""
    collection = get_user_collection(user_id)
    collection.delete(where={"document_id": document_id})


def rename_document(user_id: int, document_id: int, new_title: str) -> None:
    """هم‌گام‌سازی عنوان سند در متادیتای چانک‌ها (برای نمایش درست «منبع» در چت)"""
    collection = get_user_collection(user_id)
    found = collection.get(where={"document_id": document_id}, include=["metadatas"])
    ids = found.get("ids") or []
    if not ids:
        return
    new_metas = [{**m, "document_title": new_title} for m in found["metadatas"]]
    collection.update(ids=ids, metadatas=new_metas)


def delete_all_documents(user_id: int) -> None:
    """حذف کامل Collection یک کاربر (حذف کامل مخزن دانش)"""
    try:
        _chroma_client.delete_collection(name=_collection_name_for_user(user_id))
    except Exception:
        # اگر Collection از قبل وجود نداشت، مشکلی نیست
        pass


def search(user_id: int, query_embedding: List[float], top_k: int = 5) -> List[dict]:
    """
    جستجوی معنایی در Collection کاربر.
    خروجی: لیستی از دیکشنری‌ها شامل content, score, document_id, document_title
    """
    collection = get_user_collection(user_id)

    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
    )

    output = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, distance in zip(documents, metadatas, distances):
        # فاصله cosine را به یک امتیاز شباهت قابل‌فهم بین ۰ و ۱ تبدیل می‌کنیم
        similarity_score = max(0.0, 1 - distance)
        output.append(
            {
                "content": doc,
                "score": round(similarity_score, 4),
                "document_id": meta.get("document_id"),
                "document_title": meta.get("document_title"),
            }
        )

    return output
