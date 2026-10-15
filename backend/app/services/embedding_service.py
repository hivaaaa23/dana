"""
سرویس Embedding: تبدیل متن به بردار عددی، با استفاده از API Key خود کاربر
مسئول: نفر ۲

نکته: برای پشتیبانی از سرویس‌های Compatible با OpenAI (طبق نیازمندی فایل نهایی)
پارامتر base_url استفاده می‌شود تا کاربر بتواند سرویس دلخواهش را وارد کند.
"""
from typing import List

from openai import OpenAI, APIError

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding(
    text: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> List[float]:
    """
    یک متن را Embed می‌کند و بردار عددی برمی‌گرداند.

    نکته هماهنگی با نفر ۱: api_key باید قبل از رسیدن به این تابع، از دیتابیس
    رمزگشایی شده باشد (رمزگشایی در لایه بالاتر - Router - انجام می‌شود، نه اینجا).
    """
    if not api_key:
        raise ValueError("کاربر هنوز API Key خود را وارد نکرده است")

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.embeddings.create(model=model, input=text)
    except APIError as e:
        raise RuntimeError(f"خطا در فراخوانی سرویس Embedding: {e}") from e

    return response.data[0].embedding


def get_embeddings_batch(
    texts: List[str],
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> List[List[float]]:
    """
    نسخه دسته‌ای: برای زمانی که چند chunk با هم Embed می‌شوند (سریع‌تر از حلقه زدن
    و فراخوانی جداگانه برای هر chunk).
    """
    if not api_key:
        raise ValueError("کاربر هنوز API Key خود را وارد نکرده است")

    if not texts:
        return []

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.embeddings.create(model=model, input=texts)
    except APIError as e:
        raise RuntimeError(f"خطا در فراخوانی سرویس Embedding: {e}") from e

    # ترتیب پاسخ‌ها با ترتیب ورودی یکسان است (طبق مستندات OpenAI)
    return [item.embedding for item in response.data]
