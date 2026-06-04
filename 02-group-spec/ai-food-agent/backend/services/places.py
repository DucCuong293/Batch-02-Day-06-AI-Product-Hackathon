"""
Places Service — Geoapify + optional Google Places + Mock fallback
"""
from __future__ import annotations

from copy import deepcopy

import httpx

from config import GEOAPIFY_API_KEY, GOOGLE_PLACES_API_KEY, has_key
from services.shipping import haversine_km, estimate_shipping_fee, estimate_delivery_time

# ── Mock restaurant database — Quán thật khu vực Gia Lâm, HN ─────

MOCK_RESTAURANTS = [
    # === Phở / Bún / Nước ===
    {
        "name": "Phở Bò Gia Lâm",
        "address": "32 Ngọc Lâm, Long Biên, Hà Nội",
        "lat": 21.0452, "lon": 105.8714,
        "rating": 4.5, "total_ratings": 230,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["phở", "nước", "nóng", "ấm"],
        "meal_tags": ["breakfast", "lunch", "sáng", "trưa"],
        "menu": [
            {"name": "Phở bò tái chín", "price": 45000, "calories": 420},
            {"name": "Phở bò tái nạm gầu", "price": 55000, "calories": 480},
            {"name": "Phở gà ta xé", "price": 40000, "calories": 390},
        ],
    },
    {
        "name": "Bún Bò Huế Cô Ry",
        "address": "15 Ngô Gia Khảm, Long Biên, Hà Nội",
        "lat": 21.0398, "lon": 105.8745,
        "rating": 4.3, "total_ratings": 180,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["bún", "nước", "nóng", "cay", "ấm"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Bún bò Huế đặc biệt", "price": 50000, "calories": 510},
            {"name": "Bún bò giò heo", "price": 55000, "calories": 580},
        ],
    },
    {
        "name": "Bún Riêu Cua Bà Hoa",
        "address": "8 Đức Giang, Long Biên, Hà Nội",
        "lat": 21.0575, "lon": 105.8812,
        "rating": 4.4, "total_ratings": 150,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["bún", "nước", "nóng", "thanh"],
        "meal_tags": ["breakfast", "lunch", "sáng", "trưa"],
        "menu": [
            {"name": "Bún riêu cua đồng", "price": 40000, "calories": 380},
            {"name": "Bún riêu cua ốc", "price": 45000, "calories": 420},
        ],
    },
    # === Cơm ===
    {
        "name": "Cơm Rang Dậu 36",
        "address": "36 Ngọc Lâm, Long Biên, Hà Nội",
        "lat": 21.0445, "lon": 105.8720,
        "rating": 4.2, "total_ratings": 310,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["cơm", "nóng", "no", "đa dạng"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Cơm rang dưa bò", "price": 40000, "calories": 550},
            {"name": "Cơm gà xối mỡ", "price": 45000, "calories": 620},
            {"name": "Cơm sườn bì chả", "price": 42000, "calories": 580},
        ],
    },
    {
        "name": "Cơm Văn Phòng Nhà Tôi",
        "address": "52 Sài Đồng, Long Biên, Hà Nội",
        "lat": 21.0312, "lon": 105.9015,
        "rating": 4.1, "total_ratings": 95,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["cơm", "nóng", "no", "đa dạng", "rẻ"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Cơm văn phòng 3 món", "price": 35000, "calories": 520},
            {"name": "Cơm gà luộc", "price": 38000, "calories": 480},
            {"name": "Cơm sườn nướng", "price": 40000, "calories": 600},
        ],
    },
    # === Healthy / Giảm cân ===
    {
        "name": "Eat Clean Gia Lâm",
        "address": "20 Việt Hưng, Long Biên, Hà Nội",
        "lat": 21.0480, "lon": 105.8950,
        "rating": 4.6, "total_ratings": 120,
        "price_level": 2, "is_open": True,
        "cuisine_tags": ["healthy", "salad", "nhẹ", "thanh", "low-cal", "mát"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Salad ức gà sốt mè rang", "price": 55000, "calories": 280},
            {"name": "Poke bowl cá hồi", "price": 75000, "calories": 350},
            {"name": "Wrap rau củ + trứng", "price": 45000, "calories": 220},
        ],
    },
    # === Trà sữa / Đồ uống / Đồ ngọt (Comfort) ===
    {
        "name": "Trà Sữa ToCoToCo Long Biên",
        "address": "70 Ngọc Lâm, Long Biên, Hà Nội",
        "lat": 21.0460, "lon": 105.8695,
        "rating": 4.0, "total_ratings": 400,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["trà sữa", "ngọt", "lạnh", "mát", "comfort"],
        "meal_tags": ["snack", "chiều", "tối", "dinner"],
        "menu": [
            {"name": "Trà sữa trân châu đường đen", "price": 35000, "calories": 450},
            {"name": "Trà sữa matcha", "price": 40000, "calories": 380},
            {"name": "Trà đào cam sả", "price": 30000, "calories": 180},
        ],
    },
    {
        "name": "Bánh Ngọt Maison",
        "address": "5 Gia Lâm, Long Biên, Hà Nội",
        "lat": 21.0350, "lon": 105.9080,
        "rating": 4.3, "total_ratings": 85,
        "price_level": 2, "is_open": True,
        "cuisine_tags": ["ngọt", "bánh", "comfort", "mát"],
        "meal_tags": ["snack", "chiều", "breakfast", "sáng"],
        "menu": [
            {"name": "Bánh tiramisu", "price": 45000, "calories": 380},
            {"name": "Bánh mousse chanh dây", "price": 40000, "calories": 320},
            {"name": "Croissant bơ pháp", "price": 30000, "calories": 270},
        ],
    },
    # === Mì / Ramen ===
    {
        "name": "Mì Cay Seoul Long Biên",
        "address": "88 Ngọc Lâm, Long Biên, Hà Nội",
        "lat": 21.0468, "lon": 105.8688,
        "rating": 4.1, "total_ratings": 260,
        "price_level": 2, "is_open": True,
        "cuisine_tags": ["mì", "cay", "nóng", "ấm", "comfort"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Mì cay cấp độ 2", "price": 55000, "calories": 520},
            {"name": "Mì cay hải sản", "price": 65000, "calories": 580},
            {"name": "Tokbokki phô mai", "price": 45000, "calories": 440},
        ],
    },
    {
        "name": "Ramen Đồng Giá 49K",
        "address": "22 Sài Đồng, Long Biên, Hà Nội",
        "lat": 21.0325, "lon": 105.9000,
        "rating": 4.0, "total_ratings": 175,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["ramen", "mì", "nóng", "ấm", "nước"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Ramen tonkotsu", "price": 49000, "calories": 480},
            {"name": "Ramen gà cay", "price": 49000, "calories": 460},
        ],
    },
    # === Đồ ăn vặt / Nhanh ===
    {
        "name": "Bánh Mì Doner Kebab",
        "address": "11 Cổ Linh, Long Biên, Hà Nội",
        "lat": 21.0415, "lon": 105.8790,
        "rating": 4.2, "total_ratings": 190,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["bánh mì", "nhanh", "rẻ", "nóng"],
        "meal_tags": ["breakfast", "lunch", "snack", "sáng", "trưa", "chiều"],
        "menu": [
            {"name": "Bánh mì doner kebab", "price": 30000, "calories": 480},
            {"name": "Bánh mì gà nướng", "price": 25000, "calories": 420},
            {"name": "Bánh mì xúc xích phô mai", "price": 28000, "calories": 460},
        ],
    },
    {
        "name": "Xôi Nếp Than Cô Liên",
        "address": "43 Đức Giang, Long Biên, Hà Nội",
        "lat": 21.0560, "lon": 105.8830,
        "rating": 4.5, "total_ratings": 110,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["xôi", "nóng", "ấm", "rẻ", "no"],
        "meal_tags": ["breakfast", "sáng", "snack"],
        "menu": [
            {"name": "Xôi gà", "price": 25000, "calories": 450},
            {"name": "Xôi xéo", "price": 20000, "calories": 380},
            {"name": "Xôi lạc", "price": 15000, "calories": 350},
        ],
    },
    # === Lẩu / Nhóm ===
    {
        "name": "Lẩu Hải Sản Gia Lâm",
        "address": "99 Ngọc Lâm, Long Biên, Hà Nội",
        "lat": 21.0472, "lon": 105.8682,
        "rating": 4.3, "total_ratings": 200,
        "price_level": 3, "is_open": True,
        "cuisine_tags": ["lẩu", "nóng", "ấm", "nhóm", "comfort", "cay"],
        "meal_tags": ["dinner", "tối"],
        "menu": [
            {"name": "Lẩu Thái tom yum", "price": 180000, "calories": 800},
            {"name": "Lẩu hải sản chua cay", "price": 200000, "calories": 750},
            {"name": "Lẩu gà lá é", "price": 160000, "calories": 700},
        ],
    },
    # === Cháo ===
    {
        "name": "Cháo Ếch Thiên Ân",
        "address": "65 Nguyễn Văn Cừ, Long Biên, Hà Nội",
        "lat": 21.0385, "lon": 105.8660,
        "rating": 4.4, "total_ratings": 145,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["cháo", "nóng", "ấm", "nhẹ", "thanh", "comfort"],
        "meal_tags": ["dinner", "late_night", "tối", "đêm", "breakfast", "sáng"],
        "menu": [
            {"name": "Cháo ếch Singapore", "price": 45000, "calories": 350},
            {"name": "Cháo sườn", "price": 35000, "calories": 380},
            {"name": "Cháo gà thập cẩm", "price": 40000, "calories": 360},
        ],
    },
    # === Pizza / Western ===
    {
        "name": "Pizza Hut Long Biên",
        "address": "AEON Mall Long Biên, Long Biên, Hà Nội",
        "lat": 21.0310, "lon": 105.8745,
        "rating": 4.0, "total_ratings": 500,
        "price_level": 2, "is_open": True,
        "cuisine_tags": ["pizza", "western", "nhóm", "comfort"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Pizza hải sản size M", "price": 139000, "calories": 850},
            {"name": "Pizza gà phô mai size M", "price": 129000, "calories": 780},
            {"name": "Combo 2 người", "price": 199000, "calories": 1200},
        ],
    },
    # === Gà rán ===
    {
        "name": "Gà Rán Giòn DaKa",
        "address": "18 Bồ Đề, Long Biên, Hà Nội",
        "lat": 21.0430, "lon": 105.8670,
        "rating": 4.2, "total_ratings": 170,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["gà rán", "nóng", "comfort", "nhanh"],
        "meal_tags": ["lunch", "dinner", "snack", "trưa", "tối", "chiều"],
        "menu": [
            {"name": "Gà rán giòn 2 miếng", "price": 45000, "calories": 520},
            {"name": "Combo gà rán + khoai", "price": 59000, "calories": 680},
            {"name": "Gà sốt cay Hàn Quốc", "price": 55000, "calories": 560},
        ],
    },
    # === Chè / Đồ ngọt mát ===
    {
        "name": "Chè Bưởi Bà Thin",
        "address": "27 Việt Hưng, Long Biên, Hà Nội",
        "lat": 21.0490, "lon": 105.8960,
        "rating": 4.5, "total_ratings": 95,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["chè", "ngọt", "mát", "lạnh", "comfort", "nhẹ"],
        "meal_tags": ["snack", "chiều", "dinner", "tối"],
        "menu": [
            {"name": "Chè bưởi", "price": 20000, "calories": 180},
            {"name": "Chè khúc bạch", "price": 25000, "calories": 220},
            {"name": "Chè thập cẩm", "price": 25000, "calories": 250},
        ],
    },
    # === Bún đậu / Bún chả ===
    {
        "name": "Bún Đậu Mắm Tôm Sài Đồng",
        "address": "44 Sài Đồng, Long Biên, Hà Nội",
        "lat": 21.0305, "lon": 105.9020,
        "rating": 4.3, "total_ratings": 135,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["bún đậu", "nóng", "no", "đa dạng"],
        "meal_tags": ["lunch", "dinner", "trưa", "tối"],
        "menu": [
            {"name": "Bún đậu mắm tôm đặc biệt", "price": 50000, "calories": 580},
            {"name": "Bún đậu chả cốm", "price": 45000, "calories": 520},
        ],
    },
    {
        "name": "Bún Chả Hương Liên",
        "address": "12 Ngọc Lâm, Long Biên, Hà Nội",
        "lat": 21.0440, "lon": 105.8730,
        "rating": 4.4, "total_ratings": 210,
        "price_level": 1, "is_open": True,
        "cuisine_tags": ["bún chả", "nóng", "no", "nướng"],
        "meal_tags": ["lunch", "trưa"],
        "menu": [
            {"name": "Bún chả Hà Nội", "price": 40000, "calories": 500},
            {"name": "Bún chả nem cua bể", "price": 50000, "calories": 580},
        ],
    },
]


def _profile_match_score(profile: dict, search_text: str) -> int:
    """Đánh giá profile mock nào gần với tên quán/từ khóa Places nhất."""
    score = 0
    for tag in profile.get("cuisine_tags", []):
        if tag.lower() in search_text:
            score += 5 + len(tag)
    for item in profile.get("menu", []):
        item_name = item["name"].lower()
        if item_name in search_text or any(
            word in search_text for word in item_name.split() if len(word) > 3
        ):
            score += 3
    return score


def enrich_restaurant_with_estimated_menu(
    restaurant: dict,
    keyword: str = "",
) -> dict:
    """
    Bổ sung menu ước tính cho dữ liệu Places vốn không có menu/giá.

    Dữ liệu này luôn được gắn cờ ước tính để frontend không trình bày như giá thật.
    """
    enriched = {**restaurant}
    if enriched.get("menu"):
        return enriched

    search_text = " ".join([
        keyword,
        enriched.get("name", ""),
        *enriched.get("cuisine_tags", []),
    ]).lower().strip()
    best_profile = None
    best_score = 0
    for profile in MOCK_RESTAURANTS:
        score = _profile_match_score(profile, search_text)
        if score > best_score:
            best_profile = profile
            best_score = score

    if best_profile:
        menu = deepcopy(best_profile["menu"][:3])
        cuisine_tags = list(best_profile.get("cuisine_tags", []))
        meal_tags = list(best_profile.get("meal_tags", []))
    else:
        price_by_level = {1: 40000, 2: 65000, 3: 120000, 4: 180000}
        estimated_price = price_by_level.get(enriched.get("price_level"), 55000)
        menu = [{
            "name": f"Món phổ biến tại {enriched.get('name', 'quán')}",
            "price": estimated_price,
            "calories": 450,
        }]
        cuisine_tags = [keyword.lower()] if keyword else ["đa dạng"]
        meal_tags = ["breakfast", "lunch", "snack", "dinner", "late_night"]

    for item in menu:
        item["price_is_estimated"] = True
        item["source"] = "estimated_menu"

    enriched.update({
        "menu": menu,
        "cuisine_tags": cuisine_tags,
        "meal_tags": meal_tags,
        "menu_is_estimated": True,
    })
    return enriched


# ── API Functions ────────────────────────────────────

async def search_restaurants(
    lat: float,
    lon: float,
    keyword: str = "",
    radius_km: float = 5.0,
    max_results: int = 20,
) -> list[dict]:
    """
    Tìm quán ăn gần vị trí user.
    Ưu tiên Geoapify, sau đó Google Places, cuối cùng dùng mock data.
    """
    if has_key("GEOAPIFY_API_KEY"):
        try:
            results = await _fetch_geoapify_places(
                lat, lon, keyword, radius_km, max_results
            )
            if results:
                return results
        except Exception as e:
            print(f"[Places] Geoapify error, trying fallback: {e}")

    if has_key("GOOGLE_PLACES_API_KEY"):
        try:
            results = await _fetch_real_places(
                lat, lon, keyword, radius_km, max_results
            )
            if results:
                return results
        except Exception as e:
            print(f"[Places] API error, falling back to mock: {e}")

    return _search_mock(lat, lon, keyword, radius_km, max_results)


async def _fetch_geoapify_places(
    lat: float, lon: float, keyword: str, radius_km: float, max_results: int
) -> list[dict]:
    """Geoapify Places API. Menu, price and rating are not provided."""
    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": "catering.restaurant",
        "filter": f"circle:{lon},{lat},{int(radius_km * 1000)}",
        "bias": f"proximity:{lon},{lat}",
        "limit": max_results,
        "apiKey": GEOAPIFY_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    return [
        restaurant
        for feature in data.get("features", [])
        if (restaurant := _geoapify_feature_to_restaurant(feature, lat, lon, keyword))
    ]


def _geoapify_feature_to_restaurant(
    feature: dict, user_lat: float, user_lon: float, keyword: str = ""
) -> dict | None:
    properties = feature.get("properties", {})
    name = properties.get("name")
    if not name:
        return None

    p_lat = properties.get("lat", user_lat)
    p_lon = properties.get("lon", user_lon)
    distance_m = properties.get("distance")
    try:
        dist = float(distance_m) / 1000 if distance_m is not None else haversine_km(
            user_lat, user_lon, p_lat, p_lon
        )
    except (TypeError, ValueError):
        dist = haversine_km(user_lat, user_lon, p_lat, p_lon)

    catering = properties.get("catering") or {}
    raw = (properties.get("datasource", {}).get("raw") or {})
    cuisine_text = (
        catering.get("cuisine", "") if isinstance(catering, dict) else ""
    ) or raw.get("cuisine", "")
    cuisine_tags = [
        value.replace("_", " ").strip().lower()
        for value in str(cuisine_text).split(";")
        if value.strip()
    ]

    restaurant = {
        "name": name,
        "address": properties.get("formatted") or properties.get("address_line2", ""),
        "lat": p_lat,
        "lon": p_lon,
        "rating": 0,
        "total_ratings": 0,
        "price_level": None,
        "is_open": True,
        "open_status_source": "unknown_assumed_open",
        "opening_hours_text": properties.get("opening_hours", ""),
        "cuisine_tags": cuisine_tags,
        "distance_km": round(dist, 1),
        "shipping_fee": estimate_shipping_fee(dist),
        "delivery_time_min": estimate_delivery_time(dist),
        "source": "geoapify",
        "place_id": properties.get("place_id", ""),
    }
    return enrich_restaurant_with_estimated_menu(restaurant, keyword)


async def _fetch_real_places(
    lat: float, lon: float, keyword: str, radius_km: float, max_results: int
) -> list[dict]:
    """Google Places Nearby Search API."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lon}",
        "radius": int(radius_km * 1000),
        "type": "restaurant",
        "keyword": keyword or "quán ăn",
        "key": GOOGLE_PLACES_API_KEY,
        "language": "vi",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    api_status = data.get("status")
    if api_status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(
            f"Google Places {api_status}: {data.get('error_message', 'unknown error')}"
        )

    results = []
    for place in data.get("results", [])[:max_results]:
        geo = place.get("geometry", {}).get("location", {})
        p_lat = geo.get("lat", lat)
        p_lon = geo.get("lng", lon)
        dist = haversine_km(lat, lon, p_lat, p_lon)
        opening_hours = place.get("opening_hours", {})
        open_now = opening_hours.get("open_now")

        restaurant = {
            "name": place.get("name", "Unknown"),
            "address": place.get("vicinity", ""),
            "lat": p_lat,
            "lon": p_lon,
            "rating": place.get("rating", 0),
            "total_ratings": place.get("user_ratings_total", 0),
            "price_level": place.get("price_level"),
            "is_open": open_now if open_now is not None else True,
            "open_status_source": "google_places" if open_now is not None else "unknown_assumed_open",
            "distance_km": round(dist, 1),
            "shipping_fee": estimate_shipping_fee(dist),
            "delivery_time_min": estimate_delivery_time(dist),
            "source": "google_places",
        }
        results.append(enrich_restaurant_with_estimated_menu(restaurant, keyword))

    return results


def _search_mock(
    lat: float, lon: float, keyword: str = "", radius_km: float = 5.0, max_results: int = 10
) -> list[dict]:
    """Tìm từ mock data, thêm distance + shipping."""
    keyword_lower = keyword.lower() if keyword else ""
    results = []

    for r in MOCK_RESTAURANTS:
        dist = haversine_km(lat, lon, r["lat"], r["lon"])
        if dist > radius_km:
            continue

        # Keyword filter
        if keyword_lower:
            tags_str = " ".join(r.get("cuisine_tags", []) + [r["name"].lower()])
            menu_str = " ".join(m["name"].lower() for m in r.get("menu", []))
            if keyword_lower not in tags_str and keyword_lower not in menu_str:
                continue

        results.append({
            **r,
            "is_open": True,
            "open_status_source": "unknown_assumed_open",
            "menu_is_estimated": True,
            "distance_km": round(dist, 1),
            "shipping_fee": estimate_shipping_fee(dist),
            "delivery_time_min": estimate_delivery_time(dist),
            "source": "mock",
        })

    results.sort(key=lambda x: x["distance_km"])
    return results[:max_results]


def get_all_mock_restaurants(lat: float, lon: float) -> list[dict]:
    """Lấy tất cả quán mock với distance đã tính."""
    return _search_mock(lat, lon, "", radius_km=50, max_results=100)
