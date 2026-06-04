"""
Nutrition Service — USDA FoodData Central API + Mock fallback
"""
from __future__ import annotations

import time
import unicodedata

import httpx

from config import USDA_FDC_API_KEY, has_key
from logging_config import get_logger

logger = get_logger("nutrition")

# ── Mock nutrition database — Món Việt phổ biến ──────

MOCK_NUTRITION: dict[str, dict] = {
    # Phở / Bún
    "phở bò": {"calories": 450, "protein": 28, "fat": 12, "carbs": 55},
    "phở bò tái": {"calories": 420, "protein": 26, "fat": 10, "carbs": 52},
    "phở bò tái chín": {"calories": 420, "protein": 26, "fat": 10, "carbs": 52},
    "phở bò tái nạm gầu": {"calories": 480, "protein": 30, "fat": 14, "carbs": 52},
    "phở gà": {"calories": 380, "protein": 24, "fat": 8, "carbs": 50},
    "phở gà ta xé": {"calories": 390, "protein": 25, "fat": 9, "carbs": 48},
    "bún bò huế": {"calories": 510, "protein": 30, "fat": 18, "carbs": 52},
    "bún bò huế đặc biệt": {"calories": 510, "protein": 30, "fat": 18, "carbs": 52},
    "bún bò giò heo": {"calories": 580, "protein": 35, "fat": 22, "carbs": 52},
    "bún riêu": {"calories": 380, "protein": 22, "fat": 10, "carbs": 48},
    "bún riêu cua": {"calories": 380, "protein": 22, "fat": 10, "carbs": 48},
    "bún riêu cua đồng": {"calories": 380, "protein": 22, "fat": 10, "carbs": 48},
    "bún riêu cua ốc": {"calories": 420, "protein": 24, "fat": 12, "carbs": 50},
    "bún chả": {"calories": 500, "protein": 28, "fat": 20, "carbs": 48},
    "bún chả hà nội": {"calories": 500, "protein": 28, "fat": 20, "carbs": 48},
    "bún chả nem cua bể": {"calories": 580, "protein": 30, "fat": 24, "carbs": 52},
    "bún đậu mắm tôm": {"calories": 580, "protein": 26, "fat": 28, "carbs": 52},
    "bún đậu mắm tôm đặc biệt": {"calories": 580, "protein": 26, "fat": 28, "carbs": 52},
    "bún đậu chả cốm": {"calories": 520, "protein": 24, "fat": 22, "carbs": 50},
    # Cơm
    "cơm rang": {"calories": 550, "protein": 18, "fat": 20, "carbs": 65},
    "cơm rang dưa bò": {"calories": 550, "protein": 22, "fat": 18, "carbs": 62},
    "cơm gà": {"calories": 580, "protein": 30, "fat": 18, "carbs": 60},
    "cơm gà xối mỡ": {"calories": 620, "protein": 32, "fat": 22, "carbs": 58},
    "cơm gà luộc": {"calories": 480, "protein": 28, "fat": 12, "carbs": 58},
    "cơm sườn": {"calories": 600, "protein": 28, "fat": 22, "carbs": 62},
    "cơm sườn bì chả": {"calories": 580, "protein": 26, "fat": 20, "carbs": 62},
    "cơm sườn nướng": {"calories": 600, "protein": 28, "fat": 22, "carbs": 62},
    "cơm văn phòng": {"calories": 520, "protein": 22, "fat": 16, "carbs": 60},
    "cơm văn phòng 3 món": {"calories": 520, "protein": 22, "fat": 16, "carbs": 60},
    # Healthy
    "salad": {"calories": 250, "protein": 12, "fat": 8, "carbs": 30},
    "salad ức gà": {"calories": 280, "protein": 28, "fat": 10, "carbs": 18},
    "salad ức gà sốt mè rang": {"calories": 280, "protein": 28, "fat": 10, "carbs": 18},
    "salad cá ngừ": {"calories": 260, "protein": 24, "fat": 12, "carbs": 15},
    "poke bowl": {"calories": 350, "protein": 22, "fat": 14, "carbs": 38},
    "poke bowl cá hồi": {"calories": 350, "protein": 22, "fat": 14, "carbs": 38},
    "wrap rau củ": {"calories": 220, "protein": 10, "fat": 8, "carbs": 28},
    "wrap rau củ + trứng": {"calories": 220, "protein": 10, "fat": 8, "carbs": 28},
    # Mì
    "mì cay": {"calories": 520, "protein": 16, "fat": 18, "carbs": 68},
    "mì cay cấp độ 2": {"calories": 520, "protein": 16, "fat": 18, "carbs": 68},
    "mì cay hải sản": {"calories": 580, "protein": 20, "fat": 20, "carbs": 68},
    "ramen": {"calories": 480, "protein": 20, "fat": 16, "carbs": 58},
    "ramen tonkotsu": {"calories": 480, "protein": 20, "fat": 16, "carbs": 58},
    "ramen gà cay": {"calories": 460, "protein": 22, "fat": 14, "carbs": 56},
    "tokbokki": {"calories": 440, "protein": 10, "fat": 12, "carbs": 72},
    "tokbokki phô mai": {"calories": 440, "protein": 10, "fat": 12, "carbs": 72},
    # Comfort / Snack
    "trà sữa": {"calories": 400, "protein": 4, "fat": 12, "carbs": 68},
    "trà sữa trân châu đường đen": {"calories": 450, "protein": 4, "fat": 14, "carbs": 75},
    "trà sữa matcha": {"calories": 380, "protein": 5, "fat": 10, "carbs": 65},
    "trà đào cam sả": {"calories": 180, "protein": 1, "fat": 0, "carbs": 42},
    "bánh mì": {"calories": 450, "protein": 18, "fat": 16, "carbs": 52},
    "bánh mì doner kebab": {"calories": 480, "protein": 22, "fat": 18, "carbs": 48},
    "bánh mì gà nướng": {"calories": 420, "protein": 20, "fat": 14, "carbs": 48},
    "gà rán": {"calories": 520, "protein": 28, "fat": 28, "carbs": 30},
    "gà rán giòn": {"calories": 520, "protein": 28, "fat": 28, "carbs": 30},
    "gà rán giòn 2 miếng": {"calories": 520, "protein": 28, "fat": 28, "carbs": 30},
    "gà sốt cay hàn quốc": {"calories": 560, "protein": 26, "fat": 30, "carbs": 35},
    # Cháo
    "cháo": {"calories": 320, "protein": 14, "fat": 6, "carbs": 50},
    "cháo ếch": {"calories": 350, "protein": 18, "fat": 8, "carbs": 48},
    "cháo ếch singapore": {"calories": 350, "protein": 18, "fat": 8, "carbs": 48},
    "cháo sườn": {"calories": 380, "protein": 16, "fat": 12, "carbs": 50},
    "cháo gà": {"calories": 340, "protein": 16, "fat": 8, "carbs": 48},
    "cháo gà thập cẩm": {"calories": 360, "protein": 18, "fat": 10, "carbs": 48},
    # Khác
    "xôi": {"calories": 400, "protein": 10, "fat": 8, "carbs": 72},
    "xôi gà": {"calories": 450, "protein": 18, "fat": 12, "carbs": 65},
    "xôi xéo": {"calories": 380, "protein": 8, "fat": 10, "carbs": 68},
    "xôi lạc": {"calories": 350, "protein": 10, "fat": 8, "carbs": 60},
    "lẩu": {"calories": 750, "protein": 40, "fat": 30, "carbs": 60},
    "lẩu thái": {"calories": 800, "protein": 42, "fat": 32, "carbs": 62},
    "lẩu thái tom yum": {"calories": 800, "protein": 42, "fat": 32, "carbs": 62},
    "lẩu hải sản": {"calories": 750, "protein": 38, "fat": 28, "carbs": 60},
    "lẩu hải sản chua cay": {"calories": 750, "protein": 38, "fat": 28, "carbs": 60},
    "lẩu gà lá é": {"calories": 700, "protein": 36, "fat": 26, "carbs": 58},
    "pizza": {"calories": 850, "protein": 32, "fat": 35, "carbs": 85},
    "pizza hải sản": {"calories": 850, "protein": 30, "fat": 32, "carbs": 88},
    "chè": {"calories": 200, "protein": 4, "fat": 2, "carbs": 42},
    "chè bưởi": {"calories": 180, "protein": 2, "fat": 1, "carbs": 40},
    "chè khúc bạch": {"calories": 220, "protein": 6, "fat": 4, "carbs": 38},
    "chè thập cẩm": {"calories": 250, "protein": 4, "fat": 3, "carbs": 50},
    "bánh tiramisu": {"calories": 380, "protein": 6, "fat": 22, "carbs": 40},
    "croissant": {"calories": 270, "protein": 5, "fat": 14, "carbs": 30},
}

_NUTRITION_CACHE: dict[str, dict] = {}
_API_UNAVAILABLE_UNTIL = 0.0
_API_BACKOFF_SECONDS = 300

USDA_QUERY_ALIASES = {
    "pho": "soup pho with meat",
    "bun bo": "beef noodle soup",
    "bun rieu": "vietnamese noodle soup",
    "bun cha": "pork with rice noodles",
    "bun dau": "tofu with rice noodles",
    "com rang": "fried rice",
    "com ga": "chicken with rice",
    "com suon": "pork with rice",
    "com van phong": "rice meal",
    "mi cay": "ramen noodle soup",
    "ramen": "ramen noodle soup",
    "tra sua": "bubble tea",
    "banh mi": "banh mi sandwich",
    "ga ran": "fried chicken",
    "chao": "rice porridge",
    "xoi": "sticky rice",
    "lau": "hot pot",
    "che": "sweet dessert soup",
}


async def get_nutrition(food_name: str) -> dict:
    """
    Lấy thông tin dinh dưỡng cho món ăn.
    Ưu tiên USDA FoodData Central thật → fallback mock.
    """
    global _API_UNAVAILABLE_UNTIL

    cache_key = food_name.lower().strip()
    if cache_key in _NUTRITION_CACHE:
        return dict(_NUTRITION_CACHE[cache_key])

    if has_key("USDA_FDC_API_KEY") and time.monotonic() >= _API_UNAVAILABLE_UNTIL:
        try:
            result = await _fetch_real_nutrition(food_name)
            _NUTRITION_CACHE[cache_key] = result
            return dict(result)
        except Exception as e:
            logger.warning(f"USDA API error, backing off and using mock: {type(e).__name__}")
            _API_UNAVAILABLE_UNTIL = time.monotonic() + _API_BACKOFF_SECONDS

    result = _lookup_mock(food_name)
    _NUTRITION_CACHE[cache_key] = result
    return dict(result)


async def _fetch_real_nutrition(food_name: str) -> dict:
    """USDA FoodData Central search. Nutrient values are reported per 100g."""
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": USDA_FDC_API_KEY,
        "query": _to_usda_query(food_name),
        "pageSize": 1,
        "dataType": "Foundation,SR Legacy,Survey (FNDDS)",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 400:
            # USDA occasionally rejects the optional dataType filter; retry broadly.
            params.pop("dataType", None)
            resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    foods = data.get("foods", []) if isinstance(data, dict) else []
    if not foods:
        return _lookup_mock(food_name)

    return _extract_usda_nutrition(food_name, foods[0])


def _normalize_query(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return normalized.replace("đ", "d").strip()


def _to_usda_query(food_name: str) -> str:
    normalized = _normalize_query(food_name)
    for term in sorted(USDA_QUERY_ALIASES, key=len, reverse=True):
        if term in normalized:
            return USDA_QUERY_ALIASES[term]
    return normalized


def _extract_usda_nutrition(food_name: str, food: dict) -> dict:
    nutrients = food.get("foodNutrients", [])

    def nutrient_value(names: set[str], unit: str = "") -> float:
        for nutrient in nutrients:
            name = str(nutrient.get("nutrientName", "")).lower()
            nutrient_unit = str(nutrient.get("unitName", "")).upper()
            if name in names and (not unit or nutrient_unit == unit):
                try:
                    return float(nutrient.get("value", 0) or 0)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    calories = nutrient_value({"energy"}, "KCAL")
    protein = nutrient_value({"protein"})
    fat = nutrient_value({"total lipid (fat)"})
    carbs = nutrient_value({"carbohydrate, by difference"})
    if not any([calories, protein, fat, carbs]):
        return _lookup_mock(food_name)

    return {
        "food_name": food_name,
        "matched_food": food.get("description", ""),
        "fdc_id": food.get("fdcId"),
        "calories": round(calories),
        "protein": round(protein, 1),
        "fat": round(fat, 1),
        "carbs": round(carbs, 1),
        "basis": "per 100g",
        "source": "usda_fdc",
    }


def _lookup_mock(food_name: str) -> dict:
    """Tìm dinh dưỡng từ mock database."""
    name_lower = food_name.lower().strip()

    # Exact match
    if name_lower in MOCK_NUTRITION:
        data = MOCK_NUTRITION[name_lower]
        return {"food_name": food_name, **data, "source": "mock"}

    # Partial match
    for key, data in MOCK_NUTRITION.items():
        if key in name_lower or name_lower in key:
            return {"food_name": food_name, **data, "source": "mock"}

    # Keyword match
    for key, data in MOCK_NUTRITION.items():
        words = key.split()
        if any(w in name_lower for w in words if len(w) > 2):
            return {"food_name": food_name, **data, "source": "mock"}

    # Default
    return {
        "food_name": food_name,
        "calories": 450,
        "protein": 20,
        "fat": 15,
        "carbs": 55,
        "source": "estimated",
    }
