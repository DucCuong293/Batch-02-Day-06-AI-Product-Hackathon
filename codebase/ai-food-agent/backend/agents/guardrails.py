"""
Guardrails — Tầng bảo vệ backend cho AI Food Agent.
Detect prompt injection, out-of-scope, sanitize input, validate history.
"""
from __future__ import annotations

import re
import unicodedata
from logging_config import get_logger

logger = get_logger("guardrails")

# ── Prompt injection patterns ────────────────────────

INJECTION_PATTERNS = [
    # English injection attempts
    r"(ignore|forget|disregard|override|bypass)\s+(all\s+)?(previous|prior|above|earlier|system)\s+(instructions?|prompts?|rules?|constraints?)",
    r"you\s+are\s+now\s+(a|an|my)",
    r"(act|pretend|behave|respond)\s+(as|like)\s+(a|an|if)",
    r"new\s+instructions?:\s*",
    r"system\s*prompt\s*[:=]",
    r"from\s+now\s+on\s+you\s+(are|will|should|must)",
    r"\[system\]",
    r"<\s*system\s*>",
    r"ADMIN\s*MODE",
    r"developer\s+mode",
    r"DAN\s+mode",
    r"jailbreak",
    # Vietnamese injection attempts
    r"bỏ\s+qua\s+(toàn\s+bộ\s+)?(hướng\s+dẫn|chỉ\s+thị|lệnh|prompt)",
    r"từ\s+giờ\s+bạn\s+(là|sẽ|phải)",
    r"hãy\s+(giả\s+vờ|đóng\s+vai|làm\s+như)",
    r"thay\s+đổi\s+vai\s+trò",
]

# ── Out-of-scope patterns ────────────────────────────

OUT_OF_SCOPE_PATTERNS = [
    # Toán / Khoa học
    r"giải\s+(phương\s+trình|bài\s+toán|hệ\s+phương|đề\s+bài|tích\s+phân|đạo\s+hàm)",
    r"tính\s+(tích\s+phân|đạo\s+hàm|giới\s+hạn|xác\s+suất|diện\s+tích|thể\s+tích)",
    r"chứng\s+minh\s+(rằng|định\s+lý|bất\s+đẳng\s+thức)",
    r"(solve|calculate|compute|prove|derive)\s+(the|this|for)",
    # Lập trình
    r"viết\s+(code|chương\s+trình|script|hàm|function|class|api)",
    r"(write|create|build|make)\s+(a\s+)?(code|program|script|function|app|website)",
    r"(fix|debug|refactor)\s+(this|the|my)\s+(code|bug|error|program)",
    r"(import|def|class|function|return|const|let|var)\s+\w+",
    # Dịch thuật
    r"dịch\s+(sang|từ|ra)\s+(tiếng\s+)?(anh|trung|nhật|hàn|pháp|đức|tây\s+ban\s+nha)",
    r"translate\s+(this|the|from|to|into)",
    # Viết bài / Sáng tạo nội dung
    r"viết\s+(bài|essay|luận|thơ|truyện|email|thư|báo\s+cáo|CV|resume)",
    r"(write|compose|draft)\s+(an?\s+)?(essay|article|story|poem|email|letter|report)",
    r"tóm\s+tắt\s+(bài|văn\s+bản|tài\s+liệu|sách)",
    # Khoa học / Giải thích lý thuyết
    r"giải\s+thích\s+(chi\s+tiết\s+)?(về\s+)?(lý\s+thuyết|nguyên\s+lý|định\s+luật|công\s+thức)",
    r"(lý\s+thuyết|nguyên\s+lý|định\s+luật)\s+(tương\s+đối|lượng\s+tử|newton)",
    # Chính trị / Nhạy cảm
    r"(chính\s+trị|đảng\s+phái|bầu\s+cử|biểu\s+tình|chiến\s+tranh)",
    r"(ý\s+kiến|quan\s+điểm)\s+(về|của\s+bạn\s+về)\s+(chính|tôn\s+giáo|xã\s+hội)",
]

# ── Từ khóa liên quan ẩm thực (mở rộng) ─────────────

FOOD_CONTEXT_KEYWORDS = [
    # Thực phẩm
    "ăn", "uống", "đói", "bụng", "no", "thèm",
    "quán", "nhà hàng", "tiệm", "ship", "giao hàng",
    "ngon", "dở", "rẻ", "đắt", "giá", "budget",
    "healthy", "comfort", "kcal", "calo", "calories",
    "dinh dưỡng", "protein", "chất béo",
    "bữa sáng", "bữa trưa", "bữa tối",
    "bữa", "meal", "food", "drink",
    "nóng", "lạnh", "mát", "ấm",
    "cay", "ngọt", "mặn", "chua",
    "chay", "halal", "dị ứng", "allergy",
    # Món ăn
    "phở", "bún", "cơm", "mì", "cháo", "xôi",
    "bánh", "chè", "trà sữa", "cà phê",
    "gà", "bò", "heo", "cá", "tôm", "mực",
    "rau", "salad", "pizza", "ramen", "lẩu",
    "gà rán", "bánh mì",
    # Thời tiết ảnh hưởng ăn uống
    "mưa", "nắng",
    # Gợi ý / đổi
    "gợi ý", "đổi món", "món",
]

FOOD_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in FOOD_CONTEXT_KEYWORDS) + r")\b",
    re.IGNORECASE
)

# ── Allergy-related keywords ─────────────────────────

ALLERGY_KEYWORDS_MAP: dict[str, list[str]] = {
    "hải sản": ["tôm", "cua", "mực", "ốc", "hàu", "sò", "cá", "hải sản", "seafood"],
    "đậu phộng": ["đậu phộng", "lạc", "peanut"],
    "sữa": ["sữa", "phô mai", "cheese", "bơ", "cream", "dairy", "milk"],
    "gluten": ["gluten", "lúa mì", "wheat", "mì ý", "pasta", "bread"],
    "trứng": ["trứng", "egg"],
    "đậu nành": ["đậu nành", "tương", "đậu hũ", "đậu phụ", "tofu", "soy"],
}

ALLERGY_MENTION_PATTERNS = [
    r"(dị\s+ứng|không\s+ăn\s+được|kiêng|bị\s+ứng|allergy|allergic)\s*(với|to)?\s*(\w+)",
    r"(không\s+được\s+ăn|cấm\s+ăn|tránh)\s+(.+)",
    r"(chay|chay\s+trường|ăn\s+chay|vegetarian|vegan)",
    r"(halal|kosher)",
]

LOCATION_REQUIRED_PATTERNS = [
    r"\bvi tri (hien tai|cua toi|cua minh)\b",
    r"\b(toi|minh) dang o dau\b",
    r"\b(gan toi|gan minh|gan day|quanh day|xung quanh day|gan nhat)\b",
    r"\b(khoang cach|bao xa|cach cho toi|cach cho minh)\b",
    r"\b(chi duong|dan duong|duong di)\b",
    r"\b(ship|giao).*(den|toi) (day|cho toi|cho minh)\b",
]


# ── Core functions ───────────────────────────────────

def requires_user_location(message: str) -> bool:
    """Return True when a request cannot be answered safely without current GPS."""
    normalized = unicodedata.normalize("NFD", message.lower())
    normalized = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")
    return any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in LOCATION_REQUIRED_PATTERNS
    )

def is_prompt_injection(message: str) -> bool:
    """
    Detect prompt injection attempts.
    Trả True nếu message chứa pattern injection.
    """
    msg_lower = message.lower().strip()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            logger.warning(f"Prompt injection detected: {message[:100]}")
            return True

    return False


def is_out_of_scope(message: str) -> bool:
    """
    Detect câu hỏi ngoài phạm vi ẩm thực.
    Kiểm tra 2 tầng:
    1. Pattern matching cho các chủ đề cấm
    2. Nếu message dài mà không chứa food context → likely out-of-scope
    """
    msg_lower = message.lower().strip()

    # Tầng 1: Explicit out-of-scope patterns
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            # Nhưng nếu cũng có food context → cho qua (ví dụ: "viết code đặt đồ ăn")
            has_food = bool(FOOD_REGEX.search(msg_lower))
            if not has_food:
                logger.info(f"Out-of-scope detected: {message[:100]}")
                return True

    # Tầng 2: Message dài không liên quan ẩm thực
    if len(message) > 80:
        has_food_context = bool(FOOD_REGEX.search(msg_lower))
        if not has_food_context:
            logger.info(f"Long message without food context: {message[:100]}")
            return True

    return False


def sanitize_message(message: str, max_length: int = 1000) -> str:
    """
    Sanitize user message:
    - Giới hạn độ dài
    - Xóa ký tự điều khiển nguy hiểm
    - Giữ emoji và Unicode tiếng Việt
    """
    # Giới hạn độ dài
    message = message[:max_length]

    # Xóa control characters (giữ newline, tab)
    message = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', message)

    # Xóa zero-width characters (dùng để ẩn text)
    message = re.sub(r'[\u200b-\u200f\u2028-\u202f\u2060\ufeff]', '', message)

    return message.strip()


def validate_conversation_history(
    history: list[dict],
    max_entries: int = 20,
    max_content_length: int = 2000,
) -> list[dict]:
    """
    Validate và sanitize conversation history.
    Chặn injection qua history giả mạo.
    """
    if not isinstance(history, list):
        logger.warning("Invalid history type, returning empty")
        return []

    cleaned = []
    for i, entry in enumerate(history[-max_entries:]):
        if not isinstance(entry, dict):
            continue

        role = str(entry.get("role", "")).lower().strip()
        content = str(entry.get("content", "")).strip()

        # Chỉ cho phép role user hoặc assistant
        if role not in ("user", "assistant"):
            logger.warning(f"Invalid role '{role}' in history entry {i}, skipping")
            continue

        # Giới hạn content length
        if len(content) > max_content_length:
            content = content[:max_content_length]

        # Bỏ entry rỗng
        if not content:
            continue

        # Detect injection trong history entries
        if role == "assistant" and is_prompt_injection(content):
            logger.warning(f"Injection detected in history entry {i}, skipping")
            continue

        cleaned.append({"role": role, "content": content})

    return cleaned


def extract_allergies(message: str, session_preferences: dict | None = None) -> list[str]:
    """
    Trích xuất thông tin dị ứng từ message và session.
    Trả về danh sách ingredients cần tránh.
    """
    allergies = set()
    msg_lower = message.lower()

    # Từ message hiện tại
    for pattern in ALLERGY_MENTION_PATTERNS:
        match = re.search(pattern, msg_lower)
        if match:
            matched_text = match.group(0)
            for allergy_name, ingredients in ALLERGY_KEYWORDS_MAP.items():
                if any(ing in matched_text for ing in ingredients) or allergy_name in matched_text:
                    allergies.update(ingredients)

    # Detect trực tiếp
    for allergy_name, ingredients in ALLERGY_KEYWORDS_MAP.items():
        for ingredient in ingredients:
            if f"dị ứng {ingredient}" in msg_lower or f"không ăn được {ingredient}" in msg_lower:
                allergies.update(ingredients)
            if f"kiêng {ingredient}" in msg_lower or f"tránh {ingredient}" in msg_lower:
                allergies.update(ingredients)

    # Chay
    if re.search(r"(ăn\s+chay|chay\s+trường|vegetarian|vegan)", msg_lower):
        allergies.update(["thịt", "gà", "bò", "heo", "cá", "tôm", "mực", "hải sản"])

    # Từ session preferences
    if session_preferences and session_preferences.get("allergies"):
        allergies.update(session_preferences["allergies"])

    return sorted(allergies)


def contains_allergy_mention(message: str) -> bool:
    """Check nhanh xem message có đề cập dị ứng/kiêng kỵ không."""
    msg_lower = message.lower()
    return any(
        re.search(pattern, msg_lower) for pattern in ALLERGY_MENTION_PATTERNS
    )


# ── Canned responses ─────────────────────────────────

OUT_OF_SCOPE_RESPONSE = {
    "reply": "Mình là Yumi — chuyên gia gợi ý món ăn thôi nè! 😄 Câu hỏi đó mình không rành lắm. Nhưng mà... bạn có đói bụng không? Để mình gợi ý món gì ngon cho bạn nhé!",
    "suggestions": {},
    "clarification": {
        "needed": True,
        "options": ["🍜 Gợi ý món ăn", "🍰 Tìm đồ ăn vặt", "☕ Gợi ý đồ uống"],
    },
    "weather": {},
    "mood_detected": "bình thường",
    "session_preferences": {},
}

INJECTION_BLOCKED_RESPONSE = {
    "reply": "Ối, mình không hiểu lắm á! 😅 Mình là Yumi, chỉ biết gợi ý món ăn ngon thôi. Bạn muốn ăn gì hôm nay?",
    "suggestions": {},
    "clarification": {
        "needed": True,
        "options": ["🍜 Gợi ý bữa trưa", "🍰 Đồ ăn vặt", "☕ Đồ uống"],
    },
    "weather": {},
    "mood_detected": "bình thường",
    "session_preferences": {},
}
