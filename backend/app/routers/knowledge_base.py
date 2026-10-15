"""
Endpointهای مدیریت مخزن دانش (Knowledge Base)
مسئول: نفر ۲

نکته جداسازی داده: تمام Endpointها با Depends(get_current_user) محدود به
داده‌های همان کاربر لاگین‌شده هستند - این «خیلی مهم»ترین نیازمندی فاز اول است.

نکته هماهنگی با نفر ۱:
- get_current_user از app.dependencies (ساخته‌شده توسط نفر ۱) وارد می‌شود.
- decrypt_api_key از app.utils.security (ساخته‌شده توسط نفر ۱) وارد می‌شود.
اگر مسیر/نام این دو در پروژه واقعی فرق داشت، فقط همین دو import را اصلاح کنید.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.settings import UserSettings
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentOut,
    DocumentDetail,
    DocumentListResponse,
)
from app.services import vector_store, embedding_service
from app.services.text_extract import ExtractError, extract_text
from app.utils.security import decrypt_api_key

router = APIRouter(prefix="/api/knowledge-base", tags=["Knowledge Base"])


def _get_user_embedding_config(db: Session, user):
    """کمکی: گرفتن API Key رمزگشایی‌شده و مدل embedding انتخابی کاربر"""
    if not getattr(user, "api_key_encrypted", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ابتدا باید API Key خود را در بخش تنظیمات وارد کنید.",
        )
    api_key = decrypt_api_key(user.api_key_encrypted)

    user_settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    base_url = user_settings.api_base_url if user_settings else "https://api.openai.com/v1"
    embedding_model = (
        user_settings.embedding_model if user_settings else embedding_service.DEFAULT_EMBEDDING_MODEL
    )

    return api_key, base_url, embedding_model


def _ingest(db: Session, user, title: str, content: str, filename: str | None = None) -> Document:
    """ثبت سند + chunk + embed + ذخیره در Chroma (مشترک بین ورودی متنی و آپلود فایل)"""
    api_key, base_url, embedding_model = _get_user_embedding_config(db, user)

    chunks = vector_store.chunk_text(content)
    if not chunks:
        raise HTTPException(status_code=400, detail="متن سند خالی است.")

    # اول embed می‌کنیم تا اگر شکست خورد، رکوردی نصفه‌کاره نماند
    try:
        embeddings = embedding_service.get_embeddings_batch(
            texts=chunks, api_key=api_key, base_url=base_url, model=embedding_model
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    document = Document(
        user_id=user.id,
        title=title,
        original_filename=filename,
        content=content,
        chroma_collection_name=f"user_{user.id}_kb",
        chunk_count=len(chunks),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    vector_store.add_document(
        user_id=user.id,
        document_id=document.id,
        chunks=chunks,
        embeddings=embeddings,
        document_title=document.title,
    )
    return document


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """افزودن سند متنی. سند Chunk، Embed و در ChromaDB ذخیره می‌شود."""
    return _ingest(db, current_user, payload.title, payload.content)


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """آپلود فایل (TXT / MD / PDF / DOCX)؛ متن در سرور استخراج و مثل سند متنی پردازش می‌شود."""
    data = file.file.read(10 * 1024 * 1024 + 1)  # sync def → در threadpool اجرا می‌شود
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="حداکثر حجم فایل ۱۰ مگابایت است.")
    try:
        text = extract_text(file.filename or "", data)
    except ExtractError as e:
        raise HTTPException(status_code=400, detail=str(e))
    name = (file.filename or "document")[:255]
    return _ingest(db, current_user, (title or name).strip()[:255] or name, text, filename=name)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """لیست تمام اسناد کاربر لاگین‌شده (و فقط او)"""
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return DocumentListResponse(total=len(documents), documents=documents)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """متن کامل یک سند (فقط متعلق به کاربر لاگین‌شده)"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="سند یافت نشد.")
    return document


@router.put("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """ویرایش سند - در صورت تغییر محتوا، بردارهای قبلی حذف و دوباره ساخته می‌شوند"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="سند یافت نشد.")

    if payload.title is not None:
        document.title = payload.title

    if payload.content is not None and payload.content != document.content:
        api_key, base_url, embedding_model = _get_user_embedding_config(db, current_user)
        chunks = vector_store.chunk_text(payload.content)
        if not chunks:
            raise HTTPException(status_code=400, detail="متن سند خالی است.")

        # اول embed می‌کنیم؛ اگر شکست خورد هنوز چیزی پاک نشده و سند قبلی سالم می‌ماند
        try:
            embeddings = embedding_service.get_embeddings_batch(
                texts=chunks, api_key=api_key, base_url=base_url, model=embedding_model
            )
        except RuntimeError as e:
            db.rollback()
            raise HTTPException(status_code=502, detail=str(e))

        document.content = payload.content
        vector_store.delete_document(user_id=current_user.id, document_id=document.id)
        vector_store.add_document(
            user_id=current_user.id,
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
            document_title=document.title,
        )
        document.chunk_count = len(chunks)
    elif payload.title is not None:
        # فقط عنوان عوض شده؛ متادیتای چانک‌ها در Chroma هم باید هم‌گام شود
        vector_store.rename_document(
            user_id=current_user.id, document_id=document.id, new_title=document.title
        )

    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """حذف تکی یک سند (هم از دیتابیس رابطه‌ای، هم از Vector DB)"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="سند یافت نشد.")

    vector_store.delete_document(user_id=current_user.id, document_id=document.id)
    db.delete(document)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_documents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """حذف کامل تمام اسناد کاربر (پاک کردن کل مخزن دانش)"""
    # ابتدا Vector DB را پاک می‌کنیم؛ اگر این مرحله خطا دهد، رکوردهای SQL باقی می‌مانند.
    vector_store.delete_all_documents(user_id=current_user.id)
    db.query(Document).filter(Document.user_id == current_user.id).delete()
    db.commit()
