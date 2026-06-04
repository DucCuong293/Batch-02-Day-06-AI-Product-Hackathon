"""
Weather Service — OpenWeatherMap API + mock fallback
"""
from __future__ import annotations

from datetime import datetime

import httpx

from config import OPENWEATHERMAP_API_KEY, has_key

# ── Meal time helpers ────────────────────────────────

def get_meal_period() -> str:
    """Xác định bữa ăn dựa trên giờ hiện tại."""
    hour = datetime.now().hour
    if 5 <= hour < 10:
        return "sáng"
    if 10 <= hour < 14:
        return "trưa"
    if 14 <= hour < 17:
        return "chiều"
    if 17 <= hour < 21:
        return "tối"
    return "đêm khuya"


def get_meal_tags() -> list[str]:
    """Trả về tag bữa ăn phù hợp giờ hiện tại."""
    hour = datetime.now().hour
    if 5 <= hour < 10:
        return ["breakfast", "sáng"]
    if 10 <= hour < 14:
        return ["lunch", "trưa"]
    if 14 <= hour < 17:
        return ["snack", "chiều"]
    if 17 <= hour < 21:
        return ["dinner", "tối"]
    return ["late_night", "đêm"]


# ── Weather API ──────────────────────────────────────

async def get_weather(lat: float, lon: float) -> dict:
    """
    Lấy thời tiết hiện tại từ OpenWeatherMap.
    Trả về dict chuẩn hóa, fallback sang mock nếu không có key.
    """
    if has_key("OPENWEATHERMAP_API_KEY"):
        try:
            return await _fetch_real_weather(lat, lon)
        except Exception as e:
            print(f"[Weather] API error, falling back to mock: {e}")

    return _mock_weather()


async def _fetch_real_weather(lat: float, lon: float) -> dict:
    """Gọi OpenWeatherMap Current Weather API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric",
        "lang": "vi",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    condition = data["weather"][0]["main"].lower()
    description = data["weather"][0]["description"]
    icon = data["weather"][0]["icon"]

    return _normalize_weather(temp, humidity, condition, description, icon, is_mock=False)


def _mock_weather() -> dict:
    """Mock weather data phù hợp Hà Nội, ổn định trong từng khung 3 giờ."""
    now = datetime.now()
    month = now.month

    # Mùa hè (4-9): nóng ẩm, mùa đông (10-3): lạnh
    if 4 <= month <= 9:
        scenarios = [
            {"temp": 34, "humidity": 75, "condition": "clear", "desc": "trời nắng nóng", "icon": "01d"},
            {"temp": 31, "humidity": 85, "condition": "clouds", "desc": "trời nhiều mây", "icon": "03d"},
            {"temp": 28, "humidity": 90, "condition": "rain", "desc": "mưa rào", "icon": "10d"},
            {"temp": 33, "humidity": 70, "condition": "clear", "desc": "trời nắng", "icon": "02d"},
        ]
    else:
        scenarios = [
            {"temp": 18, "humidity": 80, "condition": "clouds", "desc": "trời lạnh u ám", "icon": "04d"},
            {"temp": 15, "humidity": 85, "condition": "drizzle", "desc": "mưa phùn lạnh", "icon": "09d"},
            {"temp": 22, "humidity": 65, "condition": "clear", "desc": "trời mát mẻ", "icon": "01d"},
            {"temp": 20, "humidity": 75, "condition": "clouds", "desc": "trời se lạnh", "icon": "03d"},
        ]

    scenario_index = (now.toordinal() + now.hour // 3) % len(scenarios)
    s = scenarios[scenario_index]
    return _normalize_weather(
        s["temp"],
        s["humidity"],
        s["condition"],
        s["desc"],
        s["icon"],
        is_mock=True,
    )


def _normalize_weather(
    temp: float,
    humidity: int,
    condition: str,
    description: str,
    icon: str,
    is_mock: bool = False,
) -> dict:
    """Chuẩn hóa output và thêm food suggestion context."""
    # Gợi ý ẩm thực dựa trên thời tiết
    if condition in ("rain", "drizzle", "thunderstorm") or temp < 20:
        food_vibe = "ấm nóng, comfort food"
        suggest_tags = ["nóng", "ấm", "súp", "nước", "cay"]
        emoji = "🌧️"
    elif temp >= 32:
        food_vibe = "mát mẻ, thanh nhẹ"
        suggest_tags = ["lạnh", "mát", "thanh", "nhẹ", "salad"]
        emoji = "☀️"
    elif condition == "clear" and 22 <= temp < 32:
        food_vibe = "thoải mái, đa dạng"
        suggest_tags = ["đa dạng"]
        emoji = "🌤️"
    else:
        food_vibe = "dễ chịu, phù hợp nhiều món"
        suggest_tags = ["đa dạng"]
        emoji = "⛅"

    meal = get_meal_period()

    return {
        "temperature": round(temp, 1),
        "humidity": humidity,
        "condition": condition,
        "description": description,
        "icon": icon,
        "emoji": emoji,
        "food_vibe": food_vibe,
        "suggest_tags": suggest_tags,
        "meal_period": meal,
        "meal_tags": get_meal_tags(),
        "context_summary": f"{emoji} {description}, {round(temp)}°C — Bữa {meal}. Gợi ý: {food_vibe}.",
        "is_mock": is_mock,
    }
