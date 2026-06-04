"""
AI Food Agent — FastAPI Backend
Endpoints cho chat, weather, và context.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend dir is on path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY, LLM_PROVIDER, LLM_MODEL
from services.weather import get_weather
from agents.food_agent import process_chat

# ── App ──────────────────────────────────────────────

app = FastAPI(
    title="AI Food Agent — Yumi",
    description="Context-aware food recommendation agent",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ───────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    provider: str | None = None
    model: str | None = None
    conversation_history: list[dict] = Field(default_factory=list)
    session_preferences: dict = Field(default_factory=dict)
    weather_context: dict | None = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: dict | list = Field(default_factory=dict)
    clarification: dict = Field(default_factory=lambda: {"needed": False, "options": []})
    weather: dict = Field(default_factory=dict)
    mood_detected: str = "bình thường"
    session_preferences: dict = Field(default_factory=dict)


# ── API Endpoints ────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": "Yumi AI Food Agent", "version": "1.1.0"}


@app.get("/api/weather")
async def api_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """Lấy thời tiết hiện tại."""
    weather = await get_weather(lat, lon)
    return weather


@app.get("/api/context")
async def api_context(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """Lấy context tổng hợp (thời tiết + thời gian + gợi ý)."""
    weather = await get_weather(lat, lon)
    return {
        "weather": weather,
        "location": {"lat": lat, "lon": lon, "city": DEFAULT_CITY},
        "defaults": {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
        },
    }


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """Chat endpoint chính — gửi tin nhắn, nhận gợi ý."""
    try:
        result = await process_chat(
            message=req.message,
            weather_context=req.weather_context,
            conversation_history=req.conversation_history,
            session_preferences=req.session_preferences,
            user_lat=req.lat,
            user_lon=req.lon,
            provider=req.provider,
            model=req.model,
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ChatResponse(
            reply=f"Xin lỗi, Yumi gặp lỗi khi xử lý: {str(e)}. Bạn thử lại nhé!",
            suggestions={},
            mood_detected="lỗi",
        )


# ── Serve Frontend ───────────────────────────────────

FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "AI Food Agent API is running. Frontend not found."}


# ── Run ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
