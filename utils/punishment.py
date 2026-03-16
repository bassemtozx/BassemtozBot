import re
from datetime import timedelta

# ديسكورد بيلزم أقصى timeout = 28 يوم
MAX_TIMEOUT_DAYS = 28


def parse_punishment_duration(text: str) -> timedelta | None:
    if not text or not text.strip():
        return None
    text = text.strip().lower()
    # أرقام عربية أو إنجليزي
    num_match = re.search(r"[\d٠-٩]+", text)
    if not num_match:
        n = 1
    else:
        s = num_match.group(0)
        for a, b in zip("٠١٢٣٤٥٦٧٨٩", "0123456789"):
            s = s.replace(a, b)
        n = max(1, int(s))
    if n <= 0:
        return None
    # دقائق، ساعة، يوم، أسبوع، شهر
    if "دقيق" in text or "minute" in text or "min" in text:
        delta = timedelta(minutes=min(n, 60 * 24 * 28))
    elif "ساع" in text or "hour" in text or "hr" in text:
        delta = timedelta(hours=min(n, 24 * 28))
    elif "يوم" in text or "day" in text:
        delta = timedelta(days=min(n, MAX_TIMEOUT_DAYS))
    elif "أسبوع" in text or "week" in text:
        delta = timedelta(weeks=min(n, 4))
    elif "شهر" in text or "month" in text:
        delta = timedelta(days=min(n * 28, MAX_TIMEOUT_DAYS))
    else:
        # افتراضي: أيام
        delta = timedelta(days=min(n, MAX_TIMEOUT_DAYS))
    return delta if delta.total_seconds() > 0 else None
