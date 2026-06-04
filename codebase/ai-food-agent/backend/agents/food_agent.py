"""
Food Agent — LLM Agent chính (OpenAI + Gemini)
Xử lý chat, detect intent/mood, gọi scoring engine, trả gợi ý.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime

from config import (
    OPENAI_API_KEY, GEMINI_API_KEY,
    LLM_PROVIDER, LLM_MODEL,
    DEFAULT_LAT, DEFAULT_LON,
    has_key,
)
from logging_config import get_logger
from agents.prompts import SYSTEM_PROMPT, CORRECTION_PROMPT
from agents.guardrails import (
    is_prompt_injection,
    is_out_of_scope,
    sanitize_message,
    validate_conversation_history,
    extract_allergies,
    contains_allergy_mention,
    requires_user_location,
    OUT_OF_SCOPE_RESPONSE,
    INJECTION_BLOCKED_RESPONSE,
)
from services.weather import get_weather
from services.places import search_restaurants, get_all_mock_restaurants
from services.nutrition import get_nutrition
from services.scoring import is_specific_food_keyword, rank_and_select_backup

logger = get_logger("food_agent")

# Timeout cho toàn bộ process_chat (giây)
PROCESS_CHAT_TIMEOUT = 30
LOCATION_PERMISSION_MESSAGE = (
    "Yumi chưa nhận được vị trí hiện tại của bạn. Hãy bật quyền Vị trí/Location "
    "cho trình duyệt, sau đó nhấn vào thanh vị trí phía trên để cập nhật rồi hỏi lại nhé."
)


FOOD_KEYWORDS = [
    "phở", "bún", "bún bò", "bún riêu", "bún chả", "bún đậu",
    "cơm", "mì", "mì cay", "ramen", "cháo", "salad", "gà rán",
    "gà", "bò", "lẩu", "pizza", "trà sữa", "bánh mì", "bánh",
    "xôi", "chè", "healthy",
]


async def process_chat(
    message: str,
    weather_context: dict | None = None,
    conversation_history: list[dict] | None = None,
    session_preferences: dict | None = None,
    user_lat: float | None = None,
    user_lon: float | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Main entry point — xử lý 1 tin nhắn chat.

    Returns:
    {
        "reply": "Tin nhắn trả lời",
        "suggestions": [{quán chính + backups}],
        "clarification": {needed, options},
        "weather": {...},
        "mood_detected": "...",
        "session_preferences": {...}
    }
    """
    location_available = user_lat is not None and user_lon is not None
    provider = provider or LLM_PROVIDER
    model = model or LLM_MODEL
    session_preferences = dict(session_preferences or {})

    # ── 0. Guardrails — sanitize & validate ──────────
    message = sanitize_message(message)
    logger.info(f"Processing chat: '{message[:80]}...'" if len(message) > 80 else f"Processing chat: '{message}'")

    # Check prompt injection
    if is_prompt_injection(message):
        logger.warning(f"Blocked prompt injection: {message[:100]}")
        return {**INJECTION_BLOCKED_RESPONSE, "session_preferences": session_preferences}

    # Check out-of-scope
    if is_out_of_scope(message):
        logger.info(f"Blocked out-of-scope: {message[:100]}")
        return {**OUT_OF_SCOPE_RESPONSE, "session_preferences": session_preferences}

    if not location_available and requires_user_location(message):
        logger.info("Current location required but GPS coordinates were not provided")
        return _location_permission_response(weather_context, session_preferences)

    lat = user_lat if location_available else DEFAULT_LAT
    lon = user_lon if location_available else DEFAULT_LON

    # Validate conversation history
    conversation_history = validate_conversation_history(conversation_history or [])
    conversation_history = _sanitize_history(conversation_history, message)

    # Extract allergies
    if contains_allergy_mention(message):
        new_allergies = extract_allergies(message, session_preferences)
        if new_allergies:
            existing = set(session_preferences.get("allergies", []))
            existing.update(new_allergies)
            session_preferences["allergies"] = sorted(existing)
            logger.info(f"Allergies updated: {session_preferences['allergies']}")

    correction = _apply_correction_preferences(message, session_preferences)

    # Determine active mood and if it should be interacted with
    message_mood = None
    lower_msg = message.lower()
    if "stress" in lower_msg or "căng thẳng" in lower_msg:
        message_mood = "stress"
    elif "vui" in lower_msg or "hào hứng" in lower_msg or "phấn khích" in lower_msg:
        message_mood = "vui"
    elif "mệt" in lower_msg or "oải" in lower_msg or "kiệt sức" in lower_msg:
        message_mood = "mệt"
    elif "buồn" in lower_msg or "chán" in lower_msg:
        message_mood = "buồn"
    elif "bình thường" in lower_msg or "ổn" in lower_msg:
        message_mood = "bình thường"

    active_mood = message_mood or session_preferences.get("mood") or "bình thường"

    # Initialize interacted_moods list if not present
    if "interacted_moods" not in session_preferences:
        session_preferences["interacted_moods"] = []

    should_interact_mood = False
    if active_mood not in session_preferences["interacted_moods"]:
        should_interact_mood = True
        session_preferences["interacted_moods"].append(active_mood)

    # Save the mood to session_preferences immediately
    session_preferences["mood"] = active_mood

    # ── 1. Get weather context ───────────────────────
    if weather_context is None:
        weather_context = await get_weather(lat, lon)

    # ── 1b. Get user location address ────────────────
    from services.maps import reverse_geocode
    user_address = await reverse_geocode(lat, lon) if location_available else ""

    # ── 2. Build context for LLM ─────────────────────
    context_block = _build_context_block(
        weather_context,
        session_preferences,
        active_mood,
        should_interact_mood,
        user_address,
        lat,
        lon,
        location_available,
    )
    logger.info(f"Context Block sent to LLM:\n{context_block}")
    if correction["is_correction"]:
        context_block += f"\n\n[HƯỚNG DẪN CORRECTION]\n{CORRECTION_PROMPT}"

    # ── 3. Call LLM to understand intent ─────────────
    llm_response = await _call_llm(
        message=message,
        context=context_block,
        history=conversation_history,
        provider=provider,
        model=model,
    )

    # ── 4. Parse LLM response ───────────────────────
    parsed = _parse_llm_response(llm_response)
    if (
        parsed.get("mood_detected") == "bình thường"
        and session_preferences.get("mood")
        and not _message_mentions_mood(message)
    ):
        parsed["mood_detected"] = session_preferences["mood"]

    direct_keywords = _extract_food_keywords(message) if not correction["is_correction"] else []
    parsed_keywords = sorted(
        set(_ensure_string_list(parsed.get("cuisine_keywords")) + direct_keywords),
        key=len,
        reverse=True,
    )
    rejected_keywords = {
        str(item).lower()
        for item in session_preferences.get("rejected_items", [])
        if str(item).lower() in FOOD_KEYWORDS
    }
    parsed_keywords = [
        keyword for keyword in parsed_keywords if keyword.lower() not in rejected_keywords
    ]
    if correction["mode"] == "restaurant" and not parsed_keywords:
        parsed_keywords = _ensure_string_list(session_preferences.get("last_cuisine_keywords"))
    parsed["cuisine_keywords"] = parsed_keywords
    if (correction["is_correction"] or direct_keywords) and parsed.get("clarification_needed"):
        parsed["clarification_needed"] = False
        parsed["suggestions_needed"] = True
        parsed["clarification_options"] = []

    # ── 5. Update session preferences ────────────────
    if parsed.get("mood_detected") and parsed["mood_detected"] != "không rõ":
        new_mood = parsed["mood_detected"]
        session_preferences["mood"] = new_mood
        if new_mood not in session_preferences.get("interacted_moods", []):
            if "interacted_moods" not in session_preferences:
                session_preferences["interacted_moods"] = []
            session_preferences["interacted_moods"].append(new_mood)
    if parsed.get("budget"):
        session_preferences["budget"] = parsed["budget"]
    if parsed.get("dietary_preference") and parsed["dietary_preference"] != "normal":
        session_preferences["dietary"] = parsed["dietary_preference"]
    if parsed.get("override_tags"):
        session_preferences["override_tags"] = _ensure_string_list(parsed["override_tags"])

    # ── 6. If clarification needed → return early ────
    if parsed.get("clarification_needed"):
        return {
            "reply": parsed.get("message", "Bạn muốn ăn gì nhỉ?"),
            "suggestions": [],
            "clarification": {
                "needed": True,
                "options": parsed.get("clarification_options", []),
            },
            "weather": weather_context,
            "mood_detected": parsed.get("mood_detected", "không rõ"),
            "session_preferences": session_preferences,
        }

    # ── 7. If suggestions needed → run scoring ───────
    suggestions = []
    if parsed.get("suggestions_needed", True):
        if not location_available:
            logger.info("Restaurant suggestions require current GPS coordinates")
            return _location_permission_response(
                weather_context,
                session_preferences,
                parsed.get("mood_detected", "bình thường"),
            )

        dietary = parsed.get("dietary_preference", "normal")
        if dietary == "normal":
            dietary = session_preferences.get("dietary", "normal")
        mood = parsed.get("mood_detected") or session_preferences.get("mood", "")
        override_tags = (
            _ensure_string_list(parsed.get("override_tags"))
            or _ensure_string_list(session_preferences.get("override_tags"))
        )
        suggestions = await _get_scored_suggestions(
            lat=lat,
            lon=lon,
            budget=parsed.get("budget") or session_preferences.get("budget"),
            cuisine_keywords=parsed_keywords,
            weather_tags=weather_context.get("suggest_tags", []),
            meal_tags=weather_context.get("meal_tags", []),
            mood_tags=list(dict.fromkeys(_mood_to_tags(mood, dietary) + override_tags)),
            rejected_items=session_preferences.get("rejected_items", []),
            rejected_restaurants=session_preferences.get("rejected_restaurants", []),
            allergy_keywords=session_preferences.get("allergies", []),
        )
        # Giới hạn số lượng gợi ý nếu người dùng yêu cầu cụ thể số lượng
        requested_count = _extract_requested_count(message)
        if requested_count is not None and requested_count > 0:
            needed_backups = max(0, requested_count - 1)
            if "backups" in suggestions:
                suggestions["backups"] = suggestions["backups"][:needed_backups]

        _remember_suggestions(session_preferences, suggestions, parsed_keywords)
        if not suggestions.get("primary"):
            parsed["message"] = (
                "Mình chưa tìm thấy lựa chọn đang mở phù hợp với yêu cầu này. "
                "Bạn thử nới ngân sách hoặc chọn một nhóm món khác nhé."
            )

    return {
        "reply": parsed.get("message", "Mình tìm được một số gợi ý cho bạn!"),
        "suggestions": suggestions,
        "clarification": {"needed": False, "options": []},
        "weather": weather_context,
        "mood_detected": parsed.get("mood_detected", "bình thường"),
        "session_preferences": session_preferences,
    }


def _location_permission_response(
    weather: dict | None,
    session_preferences: dict,
    mood_detected: str = "bình thường",
) -> dict:
    return {
        "reply": LOCATION_PERMISSION_MESSAGE,
        "suggestions": {},
        "clarification": {"needed": False, "options": []},
        "weather": weather or {},
        "mood_detected": mood_detected,
        "session_preferences": session_preferences,
        "location_required": True,
    }


def _sanitize_history(history: list[dict], current_message: str) -> list[dict]:
    """Loại tin user hiện tại nếu frontend vô tình gửi lặp trong history."""
    cleaned = [
        {"role": item.get("role", "user"), "content": item.get("content", "")}
        for item in history
        if item.get("content")
    ]
    if (
        cleaned
        and cleaned[-1]["role"] == "user"
        and cleaned[-1]["content"].strip() == current_message.strip()
    ):
        cleaned.pop()
    return cleaned[-8:]


def _ensure_string_list(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return []


def _extract_food_keywords(message: str) -> list[str]:
    message_lower = message.lower()
    return sorted([
        keyword
        for keyword in FOOD_KEYWORDS
        if keyword in message_lower
    ], key=len, reverse=True)


def _message_mentions_mood(message: str) -> bool:
    return any(
        word in message.lower()
        for word in [
            "vui", "buồn", "chán", "stress", "căng thẳng", "mệt",
            "khó chịu", "bình thường",
        ]
    )


def _append_unique(preferences: dict, key: str, values: list[str], limit: int = 20) -> None:
    existing = _ensure_string_list(preferences.get(key))
    for value in _ensure_string_list(values):
        if value and value not in existing:
            existing.append(value)
    preferences[key] = existing[-limit:]


def _apply_correction_preferences(message: str, preferences: dict) -> dict:
    """Ghi nhận món/quán bị từ chối trước khi tạo gợi ý tiếp theo."""
    message_lower = message.lower()
    restaurant_phrases = ["đổi quán", "quán khác", "không thích quán", "quán này"]
    food_phrases = [
        "đổi món", "món khác", "không thích món", "không muốn ăn",
        "gợi ý khác", "khác đi", "ăn cái khác",
    ]
    negative_phrases = ["không muốn", "không thích", "bỏ", "tránh"]

    change_restaurant = any(phrase in message_lower for phrase in restaurant_phrases)
    change_food = any(phrase in message_lower for phrase in food_phrases)
    targeted_rejection = any(phrase in message_lower for phrase in negative_phrases)
    is_correction = change_restaurant or change_food or targeted_rejection

    mode = "none"
    if change_restaurant:
        mode = "restaurant"
        _append_unique(
            preferences,
            "rejected_restaurants",
            preferences.get("last_suggested_restaurants", []),
        )
    elif change_food:
        mode = "food"
        _append_unique(
            preferences,
            "rejected_items",
            preferences.get("last_suggested_items", []),
        )

    if targeted_rejection:
        _append_unique(preferences, "rejected_items", _extract_food_keywords(message))

    if "không muốn healthy" in message_lower or "không ăn healthy" in message_lower:
        preferences["dietary"] = "comfort"
    elif "không muốn comfort" in message_lower:
        preferences["dietary"] = "healthy"

    return {"is_correction": is_correction, "mode": mode}


def _remember_suggestions(preferences: dict, suggestions: dict, keywords: list[str]) -> None:
    visible = []
    if suggestions.get("primary"):
        visible.append(suggestions["primary"])
    visible.extend(suggestions.get("backups", []))
    preferences["last_suggested_items"] = [
        item["item_name"] for item in visible if item.get("item_name")
    ]
    preferences["last_suggested_restaurants"] = list(dict.fromkeys(
        item["restaurant_name"] for item in visible if item.get("restaurant_name")
    ))
    preferences["last_cuisine_keywords"] = keywords
    preferences["last_suggestions_details"] = [
        {
            "name": item["restaurant_name"],
            "address": item.get("restaurant_address", "N/A"),
            "item": item["item_name"],
            "price": item["item_price"],
            "distance": item["distance_km"],
        }
        for item in visible
    ]


def _build_context_block(
    weather: dict,
    prefs: dict,
    active_mood: str,
    should_interact_mood: bool,
    user_address: str,
    lat: float,
    lon: float,
    location_available: bool = True,
) -> str:
    """Build context string cho LLM."""
    now = datetime.now()
    location_context = (
        f"Vị trí hiện tại của người dùng: {user_address} (Tọa độ: {lat:.4f}, {lon:.4f})"
        if location_available
        else "Vị trí hiện tại của người dùng: chưa được cấp quyền; không được coi tọa độ mặc định là vị trí người dùng."
    )
    weather_context = (
        f"Thời tiết: {weather.get('context_summary', 'N/A')}"
        if location_available
        else f"Thời tiết tham khảo: {weather.get('context_summary', 'N/A')} (chưa có GPS hiện tại)"
    )
    parts = [
        f"Thời gian: {now.strftime('%H:%M ngày %d/%m/%Y')} — Bữa {weather.get('meal_period', 'N/A')}",
        weather_context,
        location_context,
    ]
    if should_interact_mood:
        parts.append(
            f"Tâm trạng hiện tại: {active_mood} (YÊU CẦU: Đây là lần đầu tiên tâm trạng này xuất hiện hoặc được chọn. "
            f"Bạn PHẢI chào hỏi, hỏi thăm hoặc tương tác, đồng cảm khéo léo với tâm trạng này ở câu mở đầu của bạn một cách thân thiện)."
        )
    else:
        parts.append(
            f"Tâm trạng hiện tại: {active_mood} (YÊU CẦU: Bạn ĐÃ tương tác/đồng cảm với tâm trạng này ở các câu trước rồi. "
            f"Tuyệt đối KHÔNG nhắc lại, đồng cảm hay hỏi thăm về tâm trạng này nữa để tránh lặp đi lặp lại làm khách hàng khó chịu. Chỉ tập trung gợi ý món ăn)."
        )

    if prefs.get("budget"):
        parts.append(f"Budget đã nói: {prefs['budget']:,}đ")
    if prefs.get("dietary"):
        parts.append(f"Sở thích ăn uống: {prefs['dietary']}")
    if prefs.get("rejected_items"):
        parts.append(f"Món đã từ chối: {', '.join(_ensure_string_list(prefs['rejected_items']))}")
    if prefs.get("rejected_restaurants"):
        parts.append(
            f"Quán đã từ chối: {', '.join(_ensure_string_list(prefs['rejected_restaurants']))}"
        )
    if prefs.get("last_suggestions_details"):
        parts.append("\n[QUÁN ĐANG GỢI Ý TRÊN MÀN HÌNH BÊN PHẢI]:")
        for idx, item in enumerate(prefs["last_suggestions_details"], 1):
            parts.append(
                f"{idx}. Quán: {item['name']} - Địa chỉ: {item['address']} - "
                f"Món đề xuất: {item['item']} - Giá: {item['price']:,}đ - Khoảng cách: {item['distance']} km"
            )

    return "\n".join(parts)


async def _call_llm(
    message: str,
    context: str,
    history: list[dict],
    provider: str,
    model: str,
) -> str:
    """Gọi LLM (OpenAI hoặc Gemini)."""
    if provider == "openai" and has_key("OPENAI_API_KEY"):
        actual_model = model if model and "gpt" in model else "gpt-4o-mini"
        return await _call_openai(message, context, history, actual_model)
    elif provider == "gemini" and has_key("GEMINI_API_KEY"):
        actual_model = model if model and ("gemini" in model or "gemma" in model) else "gemini-2.5-flash"
        return await _call_gemini(message, context, history, actual_model)
    elif has_key("OPENAI_API_KEY"):
        return await _call_openai(message, context, history, "gpt-4o-mini")
    elif has_key("GEMINI_API_KEY"):
        return await _call_gemini(message, context, history, "gemini-2.5-flash")
    else:
        # Fallback — rule-based khi không có LLM key
        return _fallback_response(message, context)


async def _call_openai(message: str, context: str, history: list[dict], model: str) -> str:
    """OpenAI Chat Completions API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"[CONTEXT HIỆN TẠI]\n{context}"},
    ]

    # Add history (last 6 messages)
    for h in history[-6:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content or ""


async def _call_gemini(message: str, context: str, history: list[dict], model: str) -> str:
    """Google Gemini API."""
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(model)

    full_prompt = f"""[SYSTEM]\n{SYSTEM_PROMPT}\n\n[CONTEXT HIỆN TẠI]\n{context}\n\n"""

    for h in history[-6:]:
        role = "User" if h.get("role") == "user" else "Yumi"
        full_prompt += f"[{role}]: {h.get('content', '')}\n"

    full_prompt += f"[User]: {message}\n[Yumi]:"

    response = await gemini_model.generate_content_async(
        full_prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=1000,
            response_mime_type="application/json",
        ),
    )

    return response.text or ""


def _fallback_response(message: str, context: str) -> str:
    """Rule-based fallback khi không có LLM key."""
    msg_lower = message.lower()

    # Detect mood
    mood = "bình thường"
    if "stress" in msg_lower or "căng thẳng" in msg_lower:
        mood = "stress"
    elif "mệt" in msg_lower:
        mood = "mệt"
    elif any(w in msg_lower for w in ["buồn", "chán", "khó chịu"]):
        mood = "buồn"
    elif any(w in msg_lower for w in ["vui", "phấn khích", "hào hứng"]):
        mood = "vui"

    # Detect budget
    budget = None
    budget_match = re.search(r'(\d{2,3})\s*k', msg_lower)
    if budget_match:
        budget = int(budget_match.group(1)) * 1000

    # Detect dietary
    dietary = "normal"
    if any(w in msg_lower for w in ["healthy", "giảm cân", "ít calo", "lành mạnh"]):
        dietary = "healthy"
    elif any(w in msg_lower for w in ["comfort", "nuông chiều", "ngọt", "cay"]):
        dietary = "comfort"

    # Detect cuisine keywords
    keywords = _extract_food_keywords(message)

    # Detect direct override buttons/preferences
    override_tags = []
    if "cay" in msg_lower:
        override_tags.extend(["cay", "nóng", "comfort"])
    if any(w in msg_lower for w in ["ngọt", "ngọt ngào"]):
        override_tags.extend(["ngọt", "comfort"])
    if any(w in msg_lower for w in ["nhanh", "nhanh gọn"]):
        override_tags.append("nhanh")
    if any(w in msg_lower for w in ["thanh đạm", "thanh mát"]):
        override_tags.extend(["thanh", "nhẹ", "healthy"])
    override_tags = list(dict.fromkeys(override_tags))

    # Check if vague
    vague = any(w in msg_lower for w in ["ăn gì", "cũng được", "gì cũng", "không biết", "sao cũng"])

    if vague and not keywords and budget is None:
        return json.dumps({
            "message": f"Bây giờ là bữa {context.split('Bữa ')[-1].split(chr(10))[0] if 'Bữa' in context else 'ăn'} — bạn muốn ăn nhẹ nhàng thanh mát hay bữa no bụng đàng hoàng?",
            "suggestions_needed": False,
            "clarification_needed": True,
            "clarification_options": ["🥗 Nhẹ nhàng, thanh mát", "🍜 No bụng, đàng hoàng", "🍰 Nuông chiều bản thân"],
            "mood_detected": mood,
            "cuisine_keywords": [],
            "budget": budget,
            "dietary_preference": dietary,
            "override_tags": override_tags,
        }, ensure_ascii=False)

    correction_message = any(
        phrase in msg_lower
        for phrase in ["đổi món", "món khác", "đổi quán", "quán khác", "khác đi"]
    )
    return json.dumps({
        "message": (
            "Được, mình đã loại các gợi ý vừa rồi và đổi hướng ngay nhé!"
            if correction_message
            else "Mình tìm được một số gợi ý phù hợp cho bạn!"
        ),
        "suggestions_needed": True,
        "clarification_needed": False,
        "clarification_options": [],
        "mood_detected": mood,
        "cuisine_keywords": keywords,
        "budget": budget,
        "dietary_preference": dietary,
        "override_tags": override_tags,
    }, ensure_ascii=False)


def fix_truncated_json(s: str) -> str:
    """Đóng các dấu ngoặc/nháy bị thiếu trong JSON bị cắt cụt."""
    s = s.strip()
    if not s:
        return "{}"

    in_quote = False
    escape = False
    brackets = []

    clean_chars = []
    for char in s:
        if escape:
            escape = False
            clean_chars.append(char)
            continue
        if char == '\\':
            escape = True
            clean_chars.append(char)
            continue
        if char == '"':
            in_quote = not in_quote
            clean_chars.append(char)
            continue

        if not in_quote:
            if char in ('{', '['):
                brackets.append(char)
            elif char in ('}', ']') and brackets:
                if (char == '}' and brackets[-1] == '{') or (char == ']' and brackets[-1] == '['):
                    brackets.pop()
        clean_chars.append(char)

    fixed = "".join(clean_chars)

    if in_quote:
        fixed += '"'

    while brackets:
        b = brackets.pop()
        if b == '{':
            fixed += '}'
        elif b == '[':
            fixed += ']'

    return fixed


def _parse_llm_response(raw: str) -> dict:
    """Parse JSON từ LLM response, tự động sửa lỗi cắt cụt và fallback nếu format sai."""
    try:
        # Tìm JSON block
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        elif raw.strip().startswith("{"):
            json_str = raw.strip()
        else:
            # LLM trả plain text → wrap thành suggestion
            return {
                "message": raw.strip(),
                "suggestions_needed": True,
                "clarification_needed": False,
                "mood_detected": "bình thường",
                "cuisine_keywords": [],
                "budget": None,
                "dietary_preference": "normal",
            }

        # Thử parse JSON trực tiếp trước
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Nếu lỗi parse (ví dụ do bị cắt cụt), thử tự động sửa đổi cấu trúc JSON
            fixed_str = fix_truncated_json(json_str)
            return json.loads(fixed_str)

    except (json.JSONDecodeError, IndexError, Exception):
        # Fallback - trích xuất thông điệp bằng regex nếu JSON bị lỗi hoàn toàn
        import re
        message = "Mình gợi ý cho bạn nhé!"

        # Tìm '"message": "..."'
        msg_match = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        if msg_match:
            message = msg_match.group(1)
        else:
            # Tìm '"message": "...' nếu không có dấu ngoặc kép đóng
            open_msg_match = re.search(r'"message"\s*:\s*"([^"]*)', raw)
            if open_msg_match:
                message = open_msg_match.group(1)

        # Giải mã các ký tự Unicode escape (như \u1ee3) một cách an toàn mà không làm lỗi Unicode thô
        if '\\u' in message:
            try:
                message = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), message)
            except Exception:
                pass

        # Dọn dẹp ký tự thừa và ký tự escape
        message = message.replace('"', '').replace('\\n', '\n').replace('\\"', '"').strip()

        # Trích xuất các option của clarification nếu có
        options = []
        if '"clarification_options"' in raw:
            opt_section = raw.split('"clarification_options"')[-1]
            opt_matches = re.findall(r'"([^"]+)"', opt_section)
            for opt in opt_matches:
                if opt not in ["message", "suggestions_needed", "clarification_needed", "clarification_options", "mood_detected", "cuisine_keywords", "budget", "dietary_preference", "override_tags", "true", "false", "null"]:
                    if '\\u' in opt:
                        try:
                            opt = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), opt)
                        except Exception:
                            pass
                    options.append(opt.replace('\\"', '"'))

        return {
            "message": message or "Mình gợi ý cho bạn nhé!",
            "suggestions_needed": "suggestions_needed\": false" not in raw.lower() and "suggestions_needed\":f" not in raw.lower(),
            "clarification_needed": "clarification_needed\": true" in raw.lower() or len(options) > 0,
            "clarification_options": options[:3] if options else [],
            "mood_detected": "bình thường",
            "cuisine_keywords": [],
            "budget": None,
            "dietary_preference": "normal",
        }


def _mood_to_tags(mood: str, dietary: str) -> list[str]:
    """Convert mood + dietary thành tags cho scoring."""
    tags = []
    mood = mood or ""
    if mood in ("buồn", "stress", "mệt"):
        tags.extend(["comfort", "ngọt", "cay", "ấm"])
    elif mood == "vui":
        tags.extend(["đa dạng"])

    if dietary == "healthy":
        tags.extend(["healthy", "nhẹ", "thanh", "low-cal"])
    elif dietary == "comfort":
        tags.extend(["comfort", "ngọt", "cay", "nóng"])

    return tags


async def _get_scored_suggestions(
    lat: float,
    lon: float,
    budget: int | None,
    cuisine_keywords: list[str],
    weather_tags: list[str],
    meal_tags: list[str],
    mood_tags: list[str],
    rejected_items: list[str] | None = None,
    rejected_restaurants: list[str] | None = None,
    allergy_keywords: list[str] | None = None,
) -> dict:
    """Lấy quán, chấm điểm, chọn primary + backup."""
    # Tìm theo món trước để yêu cầu cụ thể không bị mất vì giới hạn quán gần nhất.
    restaurants = []
    search_keywords = [
        keyword for keyword in cuisine_keywords if is_specific_food_keyword(keyword)
    ]
    search_batches = await asyncio.gather(
        *[
            search_restaurants(
                lat,
                lon,
                keyword=keyword,
                radius_km=5,
                max_results=20,
            )
            for keyword in search_keywords[:2]
        ],
        search_restaurants(lat, lon, keyword="", radius_km=5, max_results=30),
    )
    for batch in search_batches:
        restaurants.extend(batch)
    restaurants = _deduplicate_restaurants(restaurants)

    if not restaurants:
        restaurants = get_all_mock_restaurants(lat, lon)

    # Chấm điểm & chọn backup
    result = rank_and_select_backup(
        restaurants=restaurants,
        user_lat=lat,
        user_lon=lon,
        budget=budget,
        cuisine_keywords=cuisine_keywords,
        weather_tags=weather_tags,
        meal_tags=meal_tags,
        mood_tags=mood_tags,
        rejected_items=rejected_items,
        rejected_restaurants=rejected_restaurants,
        allergy_keywords=allergy_keywords,
    )

    # Thêm nutrition song song cho primary + backups.
    async def attach_nutrition(item: dict) -> None:
        try:
            item["nutrition"] = await get_nutrition(item["item_name"])
        except Exception:
            item["nutrition"] = {
                "calories": item.get("item_calories", 0),
                "source": "estimated",
            }

    visible_items = [
        item
        for item in [result.get("primary"), *result.get("backups", [])]
        if item
    ]
    await asyncio.gather(*(attach_nutrition(item) for item in visible_items))

    return result


def _deduplicate_restaurants(restaurants: list[dict]) -> list[dict]:
    """Giữ kết quả tìm theo món đứng trước kết quả tìm rộng."""
    unique = []
    seen = set()
    for restaurant in restaurants:
        key = (
            restaurant.get("name", "").lower().strip(),
            round(restaurant.get("lat", 0), 4),
            round(restaurant.get("lon", 0), 4),
        )
        if key not in seen:
            unique.append(restaurant)
            seen.add(key)
    return unique


def _extract_requested_count(message: str) -> int | None:
    """Trích xuất số lượng gợi ý mà người dùng yêu cầu (ví dụ: 'gợi ý 3 quán', 'top 2')."""
    message_lower = message.lower()
    # Khớp: "3 quán", "3 món", "3 lựa chọn", "3 gợi ý"
    match = re.search(r'\b(\d+)\s*(quán|món|lựa chọn|gợi ý)\b', message_lower)
    if match:
        return int(match.group(1))

    # Khớp: "gợi ý 3", "lấy 3", "cho 3"
    match_verb = re.search(r'\b(gợi ý|lấy|cho|chọn|tìm)\s+(\d+)\b', message_lower)
    if match_verb:
        return int(match_verb.group(2))

    return None
