"""
تشخیص Prompt Injection (قاعده‌محور، فارسی + انگلیسی) قبل از ارسال پیام به مدل.

این یک لایه‌ی اول ساده است، نه دیوار امنیتی کامل: الگوهای رایج «دستورهای قبلی را نادیده بگیر»،
«system prompt را نشان بده»، «نقش را عوض کن / DAN» و تزریق توکن‌های نقش را می‌گیرد.
حالت‌ها (PROMPT_INJECTION_MODE): off | log (فقط ثبت) | block (ثبت + پاسخ امن بدون فراخوانی مدل).
"""
import re
import unicodedata
from dataclasses import dataclass

from app.config import settings

REFUSAL_TEXT = "این پیام شبیه تلاش برای تغییر دستورهای دستیار است و پردازش نشد. لطفاً سوالتان را درباره‌ی موضوع اصلی بپرسید."

# (دلیل، الگو) — متن قبل از تطبیق نرمال می‌شود (ی/ک عربی، اعراب، کشیده، فاصله‌ها، حروف کوچک)
_RULES: list[tuple[str, str]] = [
    ("ignore_instructions", r"(ignore|disregard|forget|override|bypass)\s+(all\s+|any\s+|the\s+|your\s+|my\s+)*(previous|prior|above|earlier|preceding|system|initial|original)?\s*(instructions?|prompts?|rules?|guidelines?|directives?|context)"),
    ("ignore_instructions", r"(دستور(ات|ها|العمل(‌ها)?)?|راهنمای?(‌ها)?|قوانین|قواعد|پرامپت|پرومپت|محدودیت(‌ها)?)\s*(های\s*)?(قبلی|پیشین|بالا|اولیه|سیستمی|سیستم)?[^.\n]{0,25}(نادیده\s*بگیر|فراموش\s*کن|کنار\s*بگذار|دور\s*بینداز|لغو\s*کن|اعمال\s*نکن|رعایت\s*نکن)"),
    ("ignore_instructions", r"(نادیده\s*بگیر|فراموش\s*کن|کنار\s*بگذار)[^.\n]{0,25}(دستور|قوانین|راهنما|پرامپت|پرومپت|محدودیت)"),
    ("reveal_system_prompt", r"(reveal|show|print|display|repeat|output|leak|tell\s+me|what\s+(is|are))\b[^.\n]{0,40}\b(system\s+prompt|initial\s+prompt|hidden\s+(prompt|instructions?)|your\s+(instructions?|rules|prompt))"),
    ("reveal_system_prompt", r"(سیستم\s*پرامپت|سیستم\s*پرومپت|پرامپت\s*سیستم|پرومپت\s*سیستم|دستورهای?\s*(سیستمی|مخفی|اولیه|داخلی)|دستورات\s*(سیستمی|مخفی|اولیه|داخلی))[^.\n]{0,30}(نشان\s*بده|بگو|چاپ\s*کن|نمایش\s*بده|بنویس|لو\s*بده|تکرار\s*کن|چیست)"),
    ("reveal_system_prompt", r"(نشان\s*بده|بگو|چاپ\s*کن|نمایش\s*بده|لو\s*بده|تکرار\s*کن)[^.\n]{0,30}(سیستم\s*پرامپت|سیستم\s*پرومپت|پرامپت\s*سیستم|پرومپت\s*سیستم|دستورهای?\s*(سیستمی|مخفی|اولیه|داخلی)|دستورات\s*(سیستمی|مخفی|اولیه|داخلی))"),
    ("role_override", r"\b(you\s+are\s+now|from\s+now\s+on\s+you|act\s+as\s+(if\s+you\s+(are|were)\s+)?(an?\s+)?(unrestricted|unfiltered|jailbroken)|pretend\s+(to\s+be|you\s+are)|developer\s+mode|jailbreak|do\s+anything\s+now|\bDAN\b)"),
    ("role_override", r"(از\s*(حالا|الان|این\s*لحظه)\s*(به\s*بعد)?\s*تو\s*(یک|یه)?|تو\s*دیگر|تو\s*دیگه)[^.\n]{0,40}(هستی|باش|شو)|(نقش|شخصیت)\s*(خودت|خود|ات|تو)?\s*را?\s*(عوض|تغییر)\s*(کن|بده)|حالت\s*(توسعه‌?دهنده|بدون\s*محدودیت|جیلبریک)|بدون\s*(هیچ\s*)?(محدودیت|فیلتر|سانسور)\s*(پاسخ|جواب)"),
    ("role_token_injection", r"(<\|?\s*(system|im_start|im_end|assistant)\s*\|?>|\[/?\s*(inst|system)\s*\]|^\s*(system|assistant)\s*:|###\s*(system|instruction)s?\b)"),
    ("exfiltrate_secrets", r"(reveal|show|print|leak|give\s+me|tell\s+me|نشان\s*بده|بگو|چاپ\s*کن|لو\s*بده)[^.\n]{0,25}(api[\s_-]?key|secret[\s_-]?key|کلید\s*(api|مخفی|رمز)|توکن\s*(دسترسی|مخفی))"),
    ("exfiltrate_secrets", r"(api[\s_-]?key|secret[\s_-]?key|کلید\s*(api|اِی‌پی‌آی|مخفی|رمز)|توکن\s*(دسترسی|مخفی)|رمز\s*عبور\s*(ادمین|کاربر|پایگاه|دیتابیس))[^.\n]{0,25}(نشان\s*بده|بگو|چاپ\s*کن|لو\s*بده|reveal|show|print|leak|give\s+me)"),
]

_COMPILED = [(reason, re.compile(pat.replace("\u200c", ""), re.IGNORECASE | re.MULTILINE)) for reason, pat in _RULES]
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u0640"), None)  # ZWSP/ZWNJ/ZWJ/WJ/BOM/کشیده
_FA_MAP = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه"})
_COMBINING = re.compile(r"[\u064b-\u065f\u0670]")  # اعراب


@dataclass(frozen=True)
class GuardResult:
    flagged: bool
    reason: str | None = None


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.translate(_ZERO_WIDTH).translate(_FA_MAP)
    text = _COMBINING.sub("", text)
    # ZWNJ حذف شده؛ دوباره فاصله‌ی ساده‌ی «می‌خواهم» به «می خواهم» برای الگوها یکدست می‌شود
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def check(text: str) -> GuardResult:
    if settings.PROMPT_INJECTION_MODE == "off" or not text:
        return GuardResult(False)
    norm = normalize(text)
    for reason, rx in _COMPILED:
        if rx.search(norm):
            return GuardResult(True, reason)
    return GuardResult(False)


def should_block(result: GuardResult) -> bool:
    return result.flagged and settings.PROMPT_INJECTION_MODE == "block"
