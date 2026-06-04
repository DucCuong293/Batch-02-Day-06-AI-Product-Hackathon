from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

import main
from agents import food_agent
from services.places import MOCK_RESTAURANTS


WEATHER = {
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


def test_chat_endpoint_runs_full_mock_recommendation_flow(monkeypatch):
    async def fake_llm(message, context, history, provider, model):
        return food_agent._fallback_response(message, context)

    async def fake_search(lat, lon, keyword="", radius_km=5, max_results=20):
        restaurants = deepcopy(MOCK_RESTAURANTS)
        for restaurant in restaurants:
            restaurant["is_open"] = True
            restaurant["source"] = "mock"
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

    response = TestClient(main.app).post("/api/chat", json={
        "message": "Trời mưa muốn ăn phở dưới 70k",
        "lat": 21.0341,
        "lon": 105.9072,
        "weather_context": WEATHER,
    })

    assert response.status_code == 200
    body = response.json()
    assert "phở" in body["suggestions"]["primary"]["item_name"].lower()
    assert body["suggestions"]["primary"]["requested_keyword_match"] is True
