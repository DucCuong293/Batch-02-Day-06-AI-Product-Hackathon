"""
Config — Load environment variables & API keys
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── LLM ──────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ── Weather ──────────────────────────────────────────
OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "")

# ── Restaurant Search ────────────────────────────────
GEOAPIFY_API_KEY: str = os.getenv("GEOAPIFY_API_KEY", "")
GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")

# ── Nutrition ────────────────────────────────────────
USDA_FDC_API_KEY: str = os.getenv("USDA_FDC_API_KEY", "")

# ── Defaults ─────────────────────────────────────────
DEFAULT_LAT: float = float(os.getenv("DEFAULT_LAT", "21.0341"))
DEFAULT_LON: float = float(os.getenv("DEFAULT_LON", "105.9072"))
DEFAULT_CITY: str = os.getenv("DEFAULT_CITY", "Gia Lâm, Hà Nội")


def has_key(key_name: str) -> bool:
    """Check if an API key is available and not placeholder."""
    val = globals().get(key_name, "")
    return bool(val) and "your-" not in val and "here" not in val
