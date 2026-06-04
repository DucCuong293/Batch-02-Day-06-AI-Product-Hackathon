from __future__ import annotations

import asyncio
from copy import deepcopy

from agents import food_agent
from services import nutrition
from services.places import (
    MOCK_RESTAURANTS,
    _geoapify_feature_to_restaurant,
    enrich_restaurant_with_estimated_menu,
)
from services.scoring import rank_and_select_backup


USER_LAT = 21.0341
USER_LON = 105.9072
FIXED_WEATHER = {
    "temperature": 27,
    "humidity": 90,
    "condition": "rain",
    "description": "mưa rào",
    "emoji": "🌧️",
    "food_vibe": "ấm nóng",
    "suggest_tags": ["nóng", "ấm", "nước"],
    "meal_period": "trưa",
    "meal_tags": ["lunch", "trưa"],
    "context_summary": "mưa rào, bữa trưa",
    "is_mock": True,
}


def _open_mock_restaurants() -> list[dict]:
    restaurants = deepcopy(MOCK_RESTAURANTS)
    for restaurant in restaurants:
        restaurant["is_open"] = True
        restaurant["open_status_source"] = "test"
        restaurant["source"] = "mock"
    return restaurants


def test_specific_food_request_is_not_replaced_by_unrelated_food():
    result = rank_and_select_backup(
        restaurants=_open_mock_restaurants(),
        user_lat=USER_LAT,
        user_lon=USER_LON,
        budget=70000,
        cuisine_keywords=["phở"],
        weather_tags=["nóng", "ấm", "nước"],
        meal_tags=["lunch", "trưa"],
    )

    assert result["primary"] is not None
    assert "phở" in result["primary"]["item_name"].lower()
    assert result["primary"]["requested_keyword_match"] is True


def test_diacritic_normalization_does_not_match_pho_inside_phong():
    result = rank_and_select_backup(
        restaurants=_open_mock_restaurants(),
        user_lat=USER_LAT,
        user_lon=USER_LON,
        cuisine_keywords=["phở"],
        weather_tags=["nóng"],
        meal_tags=["lunch"],
    )

    assert "văn phòng" not in result["primary"]["item_name"].lower()
    assert "phở" in result["primary"]["item_name"].lower()


def test_specific_food_beats_descriptive_keyword_from_llm():
    result = rank_and_select_backup(
        restaurants=_open_mock_restaurants(),
        user_lat=USER_LAT,
        user_lon=USER_LON,
        budget=70000,
        cuisine_keywords=["phở", "nóng"],
        weather_tags=["nóng", "ấm", "nước"],
        meal_tags=["lunch", "trưa"],
    )

    assert result["primary"]["specific_food_match"] is True
    assert "phở" in result["primary"]["item_name"].lower()


def test_rejected_item_is_not_recommended_again():
    restaurants = _open_mock_restaurants()
    first = rank_and_select_backup(
        restaurants=restaurants,
        user_lat=USER_LAT,
        user_lon=USER_LON,
        cuisine_keywords=["cơm"],
    )
    rejected = first["primary"]["item_name"]
    second = rank_and_select_backup(
        restaurants=restaurants,
        user_lat=USER_LAT,
        user_lon=USER_LON,
        cuisine_keywords=["cơm"],
        rejected_items=[rejected],
    )

    assert second["primary"] is not None
    assert second["primary"]["item_name"] != rejected


def test_safe_backup_is_from_same_food_family():
    restaurants = [
        {
            "name": "Phở A",
            "address": "A",
            "lat": USER_LAT,
            "lon": USER_LON,
            "rating": 4.7,
            "total_ratings": 300,
            "is_open": True,
            "cuisine_tags": ["phở", "nước"],
            "meal_tags": ["lunch"],
            "menu": [{"name": "Phở bò A", "price": 45000, "calories": 420}],
        },
        {
            "name": "Phở B",
            "address": "B",
            "lat": USER_LAT + 0.002,
            "lon": USER_LON,
            "rating": 4.5,
            "total_ratings": 200,
            "is_open": True,
            "cuisine_tags": ["phở", "nước"],
            "meal_tags": ["lunch"],
            "menu": [{"name": "Phở gà B", "price": 43000, "calories": 390}],
        },
        {
            "name": "Cơm C",
            "address": "C",
            "lat": USER_LAT + 0.001,
            "lon": USER_LON,
            "rating": 4.9,
            "total_ratings": 500,
            "is_open": True,
            "cuisine_tags": ["cơm"],
            "meal_tags": ["lunch"],
            "menu": [{"name": "Cơm rang C", "price": 40000, "calories": 550}],
        },
    ]

    result = rank_and_select_backup(
        restaurants=restaurants,
        user_lat=USER_LAT,
        user_lon=USER_LON,
        cuisine_keywords=["phở"],
        meal_tags=["lunch"],
    )
    safe = next(item for item in result["backups"] if "An toàn" in item["backup_role"])

    assert safe["food_family"] == result["primary"]["food_family"] == "phở"
    assert safe["restaurant_name"] != result["primary"]["restaurant_name"]


def test_google_place_without_menu_gets_transparent_estimated_menu():
    place = {
        "name": "Phở Thử Nghiệm",
        "address": "Hà Nội",
        "lat": USER_LAT,
        "lon": USER_LON,
        "rating": 4.5,
        "total_ratings": 100,
        "price_level": 1,
        "is_open": True,
        "source": "google_places",
    }

    enriched = enrich_restaurant_with_estimated_menu(place, "phở")

    assert enriched["menu"]
    assert enriched["menu_is_estimated"] is True
    assert all(item["price_is_estimated"] for item in enriched["menu"])
    assert "phở" in enriched["cuisine_tags"]


def test_geoapify_feature_is_mapped_and_menu_is_marked_estimated():
    feature = {
        "properties": {
            "name": "Quán Việt",
            "formatted": "Gia Lâm, Hà Nội",
            "lat": USER_LAT,
            "lon": USER_LON,
            "distance": 300,
            "catering": {"cuisine": "vietnamese;noodle"},
            "place_id": "test-place",
        }
    }

    restaurant = _geoapify_feature_to_restaurant(
        feature, USER_LAT, USER_LON, "phở"
    )

    assert restaurant["source"] == "geoapify"
    assert restaurant["distance_km"] == 0.3
    assert restaurant["menu_is_estimated"] is True
    assert all(item["price_is_estimated"] for item in restaurant["menu"])


def test_usda_nutrition_mapping_and_vietnamese_query_alias():
    food = {
        "fdcId": 123,
        "description": "Soup, pho, with meat",
        "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 77},
            {"nutrientName": "Protein", "unitName": "G", "value": 5.81},
            {"nutrientName": "Total lipid (fat)", "unitName": "G", "value": 3.33},
            {
                "nutrientName": "Carbohydrate, by difference",
                "unitName": "G",
                "value": 5.6,
            },
        ],
    }

    result = nutrition._extract_usda_nutrition("Phở bò tái chín", food)

    assert nutrition._to_usda_query("Phở bò tái chín") == "soup pho with meat"
    assert result["source"] == "usda_fdc"
    assert result["basis"] == "per 100g"
    assert result["calories"] == 77
    assert result["protein"] == 5.8


def test_correction_adds_last_items_to_rejected_preferences():
    preferences = {
        "last_suggested_items": ["Phở bò tái chín", "Bún bò Huế đặc biệt"],
        "last_suggested_restaurants": ["Phở A", "Bún B"],
    }

    correction = food_agent._apply_correction_preferences("Đổi món khác đi", preferences)

    assert correction == {"is_correction": True, "mode": "food"}
    assert preferences["rejected_items"] == preferences["last_suggested_items"]


def test_current_user_message_is_removed_from_duplicate_history():
    history = [
        {"role": "user", "content": "Muốn ăn phở"},
        {"role": "assistant", "content": "Mình gợi ý nhé"},
        {"role": "user", "content": "Đổi món khác đi"},
    ]

    cleaned = food_agent._sanitize_history(history, "Đổi món khác đi")

    assert cleaned[-1]["role"] == "assistant"
    assert all(item["content"] != "Đổi món khác đi" for item in cleaned)


def test_candidate_search_queries_requested_food_before_broad_search(monkeypatch):
    calls = []

    async def fake_search(lat, lon, keyword="", radius_km=5, max_results=20):
        calls.append(keyword)
        restaurants = _open_mock_restaurants()
        if keyword:
            return [
                restaurant
                for restaurant in restaurants
                if keyword in restaurant.get("cuisine_tags", [])
            ]
        return restaurants

    async def fake_nutrition(item_name):
        return {"food_name": item_name, "calories": 400, "source": "mock"}

    monkeypatch.setattr(food_agent, "search_restaurants", fake_search)
    monkeypatch.setattr(food_agent, "get_nutrition", fake_nutrition)

    result = asyncio.run(food_agent._get_scored_suggestions(
        lat=USER_LAT,
        lon=USER_LON,
        budget=70000,
        cuisine_keywords=["phở"],
        weather_tags=["nóng"],
        meal_tags=["lunch"],
        mood_tags=[],
    ))

    assert calls[0] == "phở"
    assert calls[-1] == ""
    assert "phở" in result["primary"]["item_name"].lower()


def test_process_chat_correction_replaces_visible_suggestions(monkeypatch):
    async def fake_llm(message, context, history, provider, model):
        return food_agent._fallback_response(message, context)

    async def fake_search(lat, lon, keyword="", radius_km=5, max_results=20):
        restaurants = _open_mock_restaurants()
        if keyword:
            return [
                restaurant
                for restaurant in restaurants
                if keyword in restaurant.get("cuisine_tags", [])
            ]
        return restaurants

    async def fake_nutrition(item_name):
        return {"food_name": item_name, "calories": 400, "source": "mock"}

    monkeypatch.setattr(food_agent, "_call_llm", fake_llm)
    monkeypatch.setattr(food_agent, "search_restaurants", fake_search)
    monkeypatch.setattr(food_agent, "get_nutrition", fake_nutrition)

    first = asyncio.run(food_agent.process_chat(
        "Muốn ăn cơm",
        weather_context=FIXED_WEATHER,
        session_preferences={},
    ))
    previous_items = set(first["session_preferences"]["last_suggested_items"])
    second = asyncio.run(food_agent.process_chat(
        "Đổi món khác đi",
        weather_context=FIXED_WEATHER,
        session_preferences=first["session_preferences"],
    ))

    assert second["suggestions"]["primary"]["item_name"] not in previous_items
    assert previous_items.issubset(set(second["session_preferences"]["rejected_items"]))


def test_direct_food_request_survives_llm_omission(monkeypatch):
    async def incomplete_llm(message, context, history, provider, model):
        return """{
            "message": "Mình tìm món nóng nhé!",
            "suggestions_needed": true,
            "clarification_needed": false,
            "mood_detected": "bình thường",
            "cuisine_keywords": ["nóng"],
            "budget": 70000,
            "dietary_preference": "normal",
            "override_tags": []
        }"""

    async def fake_search(lat, lon, keyword="", radius_km=5, max_results=20):
        restaurants = _open_mock_restaurants()
        if keyword:
            return [
                restaurant
                for restaurant in restaurants
                if keyword in restaurant.get("cuisine_tags", [])
            ]
        return restaurants

    async def fake_nutrition(item_name):
        return {"food_name": item_name, "calories": 400, "source": "mock"}

    monkeypatch.setattr(food_agent, "_call_llm", incomplete_llm)
    monkeypatch.setattr(food_agent, "search_restaurants", fake_search)
    monkeypatch.setattr(food_agent, "get_nutrition", fake_nutrition)

    result = asyncio.run(food_agent.process_chat(
        "Trời mưa muốn ăn phở dưới 70k",
        weather_context=FIXED_WEATHER,
        session_preferences={},
    ))

    assert "phở" in result["suggestions"]["primary"]["item_name"].lower()


def test_direct_food_request_skips_unnecessary_llm_clarification(monkeypatch):
    async def confused_llm(message, context, history, provider, model):
        return """{
            "message": "Bạn muốn ăn nhẹ hay no bụng?",
            "suggestions_needed": false,
            "clarification_needed": true,
            "clarification_options": ["Nhẹ", "No"],
            "mood_detected": "không rõ",
            "cuisine_keywords": [],
            "budget": 70000,
            "dietary_preference": "normal",
            "override_tags": []
        }"""

    async def fake_search(lat, lon, keyword="", radius_km=5, max_results=20):
        restaurants = _open_mock_restaurants()
        if keyword:
            return [
                restaurant
                for restaurant in restaurants
                if keyword in restaurant.get("cuisine_tags", [])
            ]
        return restaurants

    async def fake_nutrition(item_name):
        return {"food_name": item_name, "calories": 400, "source": "mock"}

    monkeypatch.setattr(food_agent, "_call_llm", confused_llm)
    monkeypatch.setattr(food_agent, "search_restaurants", fake_search)
    monkeypatch.setattr(food_agent, "get_nutrition", fake_nutrition)

    result = asyncio.run(food_agent.process_chat(
        "Muốn ăn phở dưới 70k",
        weather_context=FIXED_WEATHER,
        session_preferences={},
    ))

    assert result["clarification"]["needed"] is False
    assert "phở" in result["suggestions"]["primary"]["item_name"].lower()
