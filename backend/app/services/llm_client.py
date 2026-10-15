"""
کلاینت ارتباط با مدل زبانی (Chat Completion) با استفاده از API Key خود کاربر
مسئول: نفر ۲
"""
from typing import List

from openai import OpenAI, APIError

DEFAULT_CHAT_MODEL = "gpt-4o-mini"


def get_chat_completion(
    system_prompt: str,
    user_message: str,
    context_chunks: List[str],
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.7,
) -> str:
    """
    مطابق نیازمندی «Endpoint چت RAG»: context_chunks + system_prompt کاربر + سوال
    با هم به مدل زبانی فرستاده می‌شوند و پاسخ نهایی متنی برگردانده می‌شود.
    """
    if not api_key:
        raise ValueError("کاربر هنوز API Key خود را وارد نکرده است")

    client = OpenAI(api_key=api_key, base_url=base_url)

    context_text = (
        "\n\n---\n\n".join(context_chunks)
        if context_chunks
        else "اطلاعات مرتبطی در پایگاه دانش یافت نشد."
    )

    full_system_prompt = (
        f"{system_prompt}\n\n"
        "از اطلاعات زیر (در صورت مرتبط بودن) برای پاسخ به سوال کاربر استفاده کن. "
        "اگر پاسخ در اطلاعات زیر موجود نیست، صادقانه بگو که اطلاعات کافی نداری.\n\n"
        f"### اطلاعات مرجع:\n{context_text}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except APIError as e:
        raise RuntimeError(f"خطا در فراخوانی مدل زبانی: {e}") from e

    return response.choices[0].message.content
