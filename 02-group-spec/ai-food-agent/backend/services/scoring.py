"""
Restaurant Scoring Engine — Chấm điểm + Backup Selection
"""
from __future__ import annotations

import unicodedata
import re

from logging_config import get_logger
from services.shipping import haversine_km, estimate_shipping_fee, estimate_delivery_time
from services.maps import attach_map_links

logger = get_logger("scoring")


# ── Allergy ingredient database ──────────────────────

ALLERGY_INGREDIENT_MAP: dict[str, set[str]] = {
    "tôm": {"tôm", "shrimp", "prawn"},
    "cua": {"cua", "crab"},
    "mực": {"mực", "squid"},
    "ốc": {"ốc", "snail"},
    "cá": {"cá", "fish", "cá hồi", "cá ngừ"},
    "hải sản": {"hải sản", "seafood", "tôm", "cua", "mực", "ốc", "cá", "hàu", "sò"},
    "đậu phộng": {"đậu phộng", "lạc", "peanut"},
    "sữa": {"sữa", "phô mai", "cheese", "bơ", "cream", "milk"},
    "gluten": {"gluten", "mì", "bánh mì", "bread", "wheat"},
    "trứng": {"trứng", "egg"},
    "đậu nành": {"đậu nành", "đậu hũ", "đậu phụ", "tofu", "tương"},
    # Chay
    "thịt": {"thịt", "gà", "bò", "heo", "lợn", "vịt", "meat", "pork", "chicken", "beef"},
}


def _item_contains_allergen(item_name: str, cuisine_tags: set[str], allergy_keywords: list[str]) -> bool:
    """Kiểm tra xem món ăn có chứa thành phần gây dị ứng không."""
    if not allergy_keywords:
        return False

    check_text = _normalize_text(f"{item_name} {' '.join(cuisine_tags)}")

    for allergen in allergy_keywords:
        allergen_lower = allergen.lower().strip()
        # Check trực tiếp
        if _contains_phrase(check_text, _normalize_text(allergen_lower)):
            return True
        # Check qua ingredient map
        related_terms = ALLERGY_INGREDIENT_MAP.get(allergen_lower, set())
        for term in related_terms:
            if _contains_phrase(check_text, _normalize_text(term)):
                return True

    return False


FOOD_FAMILY_TERMS = {
    "phở": ["phở"],
    "bún": ["bún", "bún bò", "bún riêu", "bún chả", "bún đậu"],
    "cơm": ["cơm"],
    "mì": ["mì", "ramen", "tokbokki"],
    "cháo": ["cháo"],
    "healthy": ["salad", "poke", "wrap", "healthy", "eat clean"],
    "đồ ngọt": ["chè", "bánh ngọt", "tiramisu", "mousse", "trà sữa", "ngọt"],
    "đồ ăn nhanh": ["bánh mì", "gà rán", "pizza"],
    "lẩu": ["lẩu"],
    "xôi": ["xôi"],
}

SPECIFIC_FOOD_TERMS = {
    "phở", "bún", "bún bò", "bún riêu", "bún chả", "bún đậu",
    "cơm", "mì", "mì cay", "ramen", "cháo", "salad", "gà rán",
    "gà", "bò", "lẩu", "pizza", "trà sữa", "bánh mì", "bánh",
    "xôi", "chè", "healthy",
}


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.replace("đ", "d").strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    if not text or not phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _matches_term(term: str, item_name: str, tags: set[str]) -> bool:
    normalized_term = _normalize_text(term)
    normalized_item = _normalize_text(item_name)
    normalized_tags = {_normalize_text(tag) for tag in tags}
    return (
        _contains_phrase(normalized_item, normalized_term)
        or any(
            _contains_phrase(tag, normalized_term)
            or _contains_phrase(normalized_term, tag)
            for tag in normalized_tags
            if tag
        )
    )


def is_specific_food_keyword(keyword: str) -> bool:
    """Phân biệt món/nhóm món bắt buộc với tag mô tả như nóng, cay, thanh."""
    normalized_keyword = _normalize_text(keyword)
    return any(
        _contains_phrase(normalized_keyword, _normalize_text(term))
        or _contains_phrase(_normalize_text(term), normalized_keyword)
        for term in SPECIFIC_FOOD_TERMS
    )


def infer_food_family(item_name: str, cuisine_tags: list[str] | set[str] | None = None) -> str:
    """Suy ra nhóm món để chọn backup an toàn đúng cùng loại."""
    search_text = _normalize_text(
        " ".join([item_name, *(cuisine_tags or [])])
    )
    for family, terms in FOOD_FAMILY_TERMS.items():
        if any(_contains_phrase(search_text, _normalize_text(term)) for term in terms):
            return family
    return "khác"


def _is_rejected(value: str, rejected_values: list[str] | None) -> bool:
    normalized_value = _normalize_text(value)
    return any(
        rejected
        and (
            _contains_phrase(normalized_value, _normalize_text(rejected))
            or _contains_phrase(_normalize_text(rejected), normalized_value)
        )
        for rejected in (rejected_values or [])
    )


def score_restaurant_menu_item(
    restaurant: dict,
    menu_item: dict,
    user_lat: float,
    user_lon: float,
    budget: int | None = None,
    cuisine_keywords: list[str] | None = None,
    weather_tags: list[str] | None = None,
    meal_tags: list[str] | None = None,
    mood_tags: list[str] | None = None,
    allergy_keywords: list[str] | None = None,
) -> dict | None:
    """
    Chấm điểm 1 cặp (quán, món) theo 5 tiêu chí.

    score = 0.30 * food_match + 0.25 * delivery_time + 0.20 * rating + 0.15 * budget_fit + 0.10 * reliability

    Returns dict với score + chi tiết breakdown.
    """
    cuisine_keywords = cuisine_keywords or []
    weather_tags = weather_tags or []
    meal_tags = meal_tags or []
    mood_tags = mood_tags or []
    allergy_keywords = allergy_keywords or []

    # ── Allergy filter — skip nếu chứa allergen ──────
    r_tags = set(restaurant.get("cuisine_tags", []))
    if allergy_keywords and _item_contains_allergen(
        menu_item["name"], r_tags, allergy_keywords
    ):
        return None  # Bỏ qua món có chứa allergen

    dist = restaurant.get("distance_km")
    if dist is None:
        dist = haversine_km(user_lat, user_lon, restaurant["lat"], restaurant["lon"])

    ship_fee = estimate_shipping_fee(dist)
    delivery_time = estimate_delivery_time(dist)
    total_cost = menu_item["price"] + ship_fee

    # ── 1. Food Match Score (0-100) ──────────────────
    food_score = 0
    r_meal_tags = set(restaurant.get("meal_tags", []))
    item_name_lower = menu_item["name"].lower()

    # Keyword match
    matched_keywords = []
    matched_specific_keywords = []
    for kw in cuisine_keywords:
        if _matches_term(kw, item_name_lower, r_tags):
            matched_keywords.append(kw)
            if is_specific_food_keyword(kw):
                matched_specific_keywords.append(kw)
            food_score += 45

    # Weather compatibility
    for wt in weather_tags:
        if wt in r_tags:
            food_score += 15

    # Meal time compatibility
    for mt in meal_tags:
        if mt in r_meal_tags:
            food_score += 15

    # Mood compatibility
    for mood in mood_tags:
        if mood in r_tags:
            food_score += 20

    food_score = min(food_score, 100)

    # ── 2. Delivery Time Score (0-100) ───────────────
    if delivery_time <= 15:
        time_score = 100
    elif delivery_time <= 25:
        time_score = 80
    elif delivery_time <= 35:
        time_score = 60
    elif delivery_time <= 45:
        time_score = 40
    else:
        time_score = 20

    # ── 3. Rating Score (0-100) ──────────────────────
    rating = restaurant.get("rating", 0)
    total_ratings = restaurant.get("total_ratings", 0)
    rating_score = rating * 20  # 5.0 → 100
    # Bonus cho quán nhiều review
    if total_ratings > 200:
        rating_score = min(rating_score + 10, 100)
    elif total_ratings < 50:
        rating_score = max(rating_score - 10, 0)

    # ── 4. Budget Fit Score (0-100) ──────────────────
    if budget is None:
        budget_score = 70  # Neutral
    elif total_cost <= budget:
        # Càng vừa budget càng tốt (không quá rẻ cũng ko quá đắt)
        ratio = total_cost / budget
        if ratio >= 0.7:
            budget_score = 100  # Vừa khít
        elif ratio >= 0.5:
            budget_score = 85
        else:
            budget_score = 70  # Rẻ quá so với budget
    elif total_cost <= budget * 1.15:
        budget_score = 40  # Hơi vượt
    else:
        budget_score = 10  # Vượt xa budget

    # ── 5. Reliability Score (0-100) ─────────────────
    reliability = 50
    if restaurant.get("is_open", True):
        reliability += 30
    else:
        reliability -= 40
    if restaurant.get("open_status_source") == "unknown_assumed_open":
        reliability -= 15
    if dist <= 2:
        reliability += 15
    elif dist <= 4:
        reliability += 5
    if rating >= 4.0:
        reliability += 10
    reliability = max(0, min(reliability, 100))

    # ── Weighted Total ───────────────────────────────
    total_score = (
        0.30 * food_score
        + 0.25 * time_score
        + 0.20 * rating_score
        + 0.15 * budget_score
        + 0.10 * reliability
    )

    return {
        "restaurant_name": restaurant["name"],
        "restaurant_address": restaurant.get("address", ""),
        "restaurant_rating": rating,
        "restaurant_total_ratings": total_ratings,
        "is_open": restaurant.get("is_open", True),
        "restaurant_lat": restaurant.get("lat"),
        "restaurant_lon": restaurant.get("lon"),
        "restaurant_source": restaurant.get("source", "unknown"),
        "open_status_source": restaurant.get("open_status_source", "unknown"),
        "item_name": menu_item["name"],
        "item_price": menu_item["price"],
        "item_calories": menu_item.get("calories", 0),
        "price_is_estimated": menu_item.get(
            "price_is_estimated",
            restaurant.get("menu_is_estimated", False),
        ),
        "food_family": infer_food_family(menu_item["name"], r_tags),
        "requested_keyword_match": bool(matched_keywords),
        "specific_food_match": bool(matched_specific_keywords),
        "matched_keywords": matched_keywords,
        "matched_specific_keywords": matched_specific_keywords,
        "distance_km": round(dist, 1),
        "shipping_fee": ship_fee,
        "total_cost": total_cost,
        "delivery_time_min": delivery_time,
        "score": round(total_score, 1),
        "score_breakdown": {
            "food_match": round(food_score, 1),
            "delivery_time": round(time_score, 1),
            "rating": round(rating_score, 1),
            "budget_fit": round(budget_score, 1),
            "reliability": round(reliability, 1),
        },
    }


def rank_and_select_backup(
    restaurants: list[dict],
    user_lat: float,
    user_lon: float,
    budget: int | None = None,
    cuisine_keywords: list[str] | None = None,
    weather_tags: list[str] | None = None,
    meal_tags: list[str] | None = None,
    mood_tags: list[str] | None = None,
    rejected_items: list[str] | None = None,
    rejected_restaurants: list[str] | None = None,
    allergy_keywords: list[str] | None = None,
) -> dict:
    """
    Chấm điểm tất cả (quán, món) pairs → chọn quán chính + 2-3 backup.

    Backup theo vai trò:
    - Backup 1 (🛡️ An toàn): Cùng loại món, rating ổn
    - Backup 2 (⚡ Nhanh): Giao nhanh nhất
    - Backup 3 (💰 Tiết kiệm): Tổng giá rẻ nhất

    Returns:
    {
        "primary": {...},
        "backups": [{...}, {...}, ...],
        "all_scored": [...]
    }
    """
    all_scored = []

    for r in restaurants:
        if not r.get("is_open", True):
            continue
        if _is_rejected(r.get("name", ""), rejected_restaurants):
            continue
        for item in r.get("menu", []):
            if _is_rejected(item.get("name", ""), rejected_items):
                continue

            # Budget hard filter: skip nếu vượt quá 50% budget
            distance = r.get("distance_km")
            if distance is None:
                distance = haversine_km(user_lat, user_lon, r["lat"], r["lon"])
            shipping_fee = r.get("shipping_fee", estimate_shipping_fee(distance))
            if budget and (item["price"] + shipping_fee) > budget * 1.5:
                continue

            scored = score_restaurant_menu_item(
                restaurant=r,
                menu_item=item,
                user_lat=user_lat,
                user_lon=user_lon,
                budget=budget,
                cuisine_keywords=cuisine_keywords,
                weather_tags=weather_tags,
                meal_tags=meal_tags,
                mood_tags=mood_tags,
                allergy_keywords=allergy_keywords,
            )
            if scored is not None:  # None = filtered by allergy
                all_scored.append(scored)

    if not all_scored:
        return {"primary": None, "backups": [], "all_scored": []}

    specific_food_requested = any(
        is_specific_food_keyword(keyword)
        for keyword in (cuisine_keywords or [])
    )
    if specific_food_requested and not any(item["specific_food_match"] for item in all_scored):
        return {"primary": None, "backups": [], "all_scored": all_scored[:10]}

    # Món/nhóm món bắt buộc luôn được ưu tiên trước tag mô tả và các yếu tố phụ.
    all_scored.sort(
        key=lambda x: (
            x["specific_food_match"] if specific_food_requested else x["requested_keyword_match"],
            x["score"],
        ),
        reverse=True,
    )

    primary = all_scored[0]

    # ── Backup Selection ─────────────────────────────
    backups = []
    used_restaurants = {primary["restaurant_name"]}

    # Backup 1: An toàn — đúng cùng nhóm món, khác quán
    for s in all_scored[1:]:
        if (
            s["restaurant_name"] not in used_restaurants
            and s["food_family"] == primary["food_family"]
            and s["food_family"] != "khác"
        ):
            s["backup_role"] = "🛡️ An toàn"
            s["backup_reason"] = (
                f"Cùng nhóm {primary['food_family']} — chọn nếu "
                f"{primary['restaurant_name']} hết món hoặc đóng cửa"
            )
            backups.append(s)
            used_restaurants.add(s["restaurant_name"])
            break

    # Backup 2: Nhanh — giao nhanh nhất (khác quán chính)
    fast_sorted = sorted(
        [s for s in all_scored if s["restaurant_name"] not in used_restaurants],
        key=lambda x: x["delivery_time_min"],
    )
    if fast_sorted:
        fb = fast_sorted[0]
        fb["backup_role"] = "⚡ Giao nhanh"
        fb["backup_reason"] = f"Giao chỉ {fb['delivery_time_min']} phút — chọn nếu bạn cần nhanh"
        backups.append(fb)
        used_restaurants.add(fb["restaurant_name"])

    # Backup 3: Rẻ — tổng giá thấp nhất (khác quán chính)
    cheap_sorted = sorted(
        [s for s in all_scored if s["restaurant_name"] not in used_restaurants],
        key=lambda x: x["total_cost"],
    )
    if cheap_sorted:
        cb = cheap_sorted[0]
        cb["backup_role"] = "💰 Tiết kiệm"
        cb["backup_reason"] = f"Tổng chỉ {cb['total_cost']:,}đ — tiết kiệm nhất"
        backups.append(cb)

    primary["backup_role"] = "🏆 Quán chính"
    primary["backup_reason"] = (
        "Đúng món bạn yêu cầu và có điểm tổng thể tốt nhất"
        if primary["specific_food_match"]
        else "Phù hợp nhất với yêu cầu của bạn"
    )

    # ── Attach map links ─────────────────────────────
    attach_map_links(primary, user_lat, user_lon)
    for backup in backups:
        attach_map_links(backup, user_lat, user_lon)

    logger.info(
        f"Scored {len(all_scored)} items, primary: {primary['item_name']} "
        f"at {primary['restaurant_name']} (score={primary['score']})"
    )

    return {
        "primary": primary,
        "backups": backups,
        "all_scored": all_scored[:10],  # Top 10 for reference
    }
