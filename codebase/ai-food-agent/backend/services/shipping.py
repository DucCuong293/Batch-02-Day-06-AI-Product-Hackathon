"""
Shipping Fee Calculator
Công thức: 15,000đ cho 2km đầu + 5,000đ/km tiếp theo
"""
from __future__ import annotations

import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách giữa 2 tọa độ bằng công thức Haversine (km)."""
    R = 6371  # Bán kính Trái Đất (km)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def estimate_shipping_fee(distance_km: float) -> int:
    """
    Ước tính phí ship dựa trên khoảng cách.
    - 2km đầu: 15,000đ
    - Mỗi km tiếp theo: +5,000đ
    """
    if distance_km <= 0:
        return 0
    if distance_km <= 2.0:
        return 15000
    extra_km = math.ceil(distance_km - 2.0)
    return 15000 + extra_km * 5000


def estimate_delivery_time(distance_km: float) -> int:
    """Ước tính thời gian giao hàng (phút) dựa trên khoảng cách."""
    # Chuẩn bị: ~10 phút, tốc độ giao: ~20km/h trung bình nội thành
    prep_time = 10
    travel_time = math.ceil(distance_km / 20 * 60)
    return prep_time + travel_time


def calculate_total_cost(food_price: int, distance_km: float) -> dict:
    """Tính tổng chi phí thực tế (giá món + phí ship)."""
    ship_fee = estimate_shipping_fee(distance_km)
    return {
        "food_price": food_price,
        "shipping_fee": ship_fee,
        "total": food_price + ship_fee,
        "distance_km": round(distance_km, 1),
        "delivery_time_min": estimate_delivery_time(distance_km),
    }
