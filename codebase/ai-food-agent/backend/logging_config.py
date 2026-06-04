"""
Structured Logging — Cấu hình logging thống nhất cho toàn bộ backend.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

# ── Request ID tracking ─────────────────────────────
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def generate_request_id() -> str:
    """Tạo request ID ngắn gọn cho tracing."""
    return uuid.uuid4().hex[:12]


# ── Custom Formatter ─────────────────────────────────

class RequestFormatter(logging.Formatter):
    """Formatter tự động gắn request_id vào mọi log line."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_var.get("-")
        return super().format(record)


# ── Setup ────────────────────────────────────────────

def setup_logging(level: int = logging.INFO) -> None:
    """Khởi tạo logging config cho toàn bộ app."""
    formatter = RequestFormatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-20s | req=%(request_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)

    # Xóa handler cũ nếu có (tránh duplicate khi reload)
    for existing in root.handlers[:]:
        root.removeHandler(existing)

    root.addHandler(handler)

    # Giảm noise từ thư viện bên ngoài
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Lấy logger theo tên module."""
    return logging.getLogger(name)
