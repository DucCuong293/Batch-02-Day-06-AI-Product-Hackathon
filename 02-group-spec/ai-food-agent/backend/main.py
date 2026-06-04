"""
AI Food Agent — FastAPI Backend
Endpoints cho chat, weather, và context.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Ensure backend dir is on path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from logging_config import setup_logging, get_logger, request_id_var, generate_request_id

# Initialize logging FIRST
setup_logging()
logger = get_logger("main")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY, LLM_PROVIDER, LLM_MODEL
from services.weather import get_weather
from services.maps import reverse_geocode
from agents.food_agent import process_chat

# ── Rate Limiter ─────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

# ── App ──────────────────────────────────────────────

app = FastAPI(
    title="AI Food Agent — Yumi",
    description="Context-aware food recommendation agent",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — configurable, mở rộng cho production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID Middleware ────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Gắn request ID vào mọi request để tracing."""
    req_id = generate_request_id()
    request_id_var.set(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# ── Models ───────────────────────────────────────────

class HistoryEntry(BaseModel):
    role: str = "user"
    content: str = ""

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("user", "assistant"):
            raise ValueError("Role must be 'user' or 'assistant'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        return v[:2000]  # Giới hạn content length


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    provider: str | None = None
    model: str | None = None
    conversation_history: list[dict] = Field(default_factory=list, max_length=20)
    session_preferences: dict = Field(default_factory=dict)
    weather_context: dict | None = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: dict | list = Field(default_factory=dict)
    clarification: dict = Field(default_factory=lambda: {"needed": False, "options": []})
    weather: dict = Field(default_factory=dict)
    mood_detected: str = "bình thường"
    session_preferences: dict = Field(default_factory=dict)


# ── Safe error message ───────────────────────────────

def _safe_error_message(e: Exception) -> str:
    """Sanitize error message — không leak sensitive info."""
    msg = str(e)
    # Ẩn API keys, paths, stack traces
    sensitive_patterns = [
        ("sk-", "sk-***"),
        ("key=", "key=***"),
        ("api_key", "api_key=***"),
    ]
    for pattern, replacement in sensitive_patterns:
        if pattern in msg.lower():
            msg = "Internal processing error"
            break
    # Giới hạn độ dài
    return msg[:200] if len(msg) > 200 else msg


# ── API Endpoints ────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": "Yumi AI Food Agent", "version": "2.0.0"}


@app.get("/api/weather")
@limiter.limit("60/minute")
async def api_weather(request: Request, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """Lấy thời tiết hiện tại."""
    weather = await get_weather(lat, lon)
    return weather


@app.get("/api/context")
@limiter.limit("60/minute")
async def api_context(request: Request, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """Lấy context tổng hợp (thời tiết + thời gian + gợi ý)."""
    weather = await get_weather(lat, lon)
    address = await reverse_geocode(lat, lon)
    return {
        "weather": weather,
        "location": {"lat": lat, "lon": lon, "city": address or DEFAULT_CITY},
        "defaults": {
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
        },
    }


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def api_chat(request: Request, req: ChatRequest):
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
    except asyncio.TimeoutError:
        logger.error("Chat request timed out")
        return ChatResponse(
            reply="Xin lỗi, Yumi xử lý hơi lâu. Bạn thử lại nhé! ⏰",
            suggestions={},
            mood_detected="lỗi",
        )
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {e}", exc_info=True)
        safe_msg = _safe_error_message(e)
        return ChatResponse(
            reply=f"Xin lỗi, Yumi gặp lỗi khi xử lý. Bạn thử lại nhé! 🙏",
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
    logger.info("Starting Yumi AI Food Agent v2.0.0")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
