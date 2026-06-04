"""
Maps Service — Google Maps links & GrabFood/ShopeeFood deep links
"""
from __future__ import annotations

from urllib.parse import quote
import httpx
from config import GEOAPIFY_API_KEY, has_key
from services.cache import address_cache


def generate_google_maps_url(
    name: str,
    lat: float | None = None,
    lon: float | None = None,
    address: str = "",
) -> str:
    """
    Tạo Google Maps URL cho chỉ đường đến quán.

    Ưu tiên tọa độ (chính xác hơn), fallback sang tên + địa chỉ.
    """
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    query = f"{name} {address}".strip()
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"


def generate_directions_url(
    user_lat: float,
    user_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> str:
    """Tạo Google Maps Directions URL từ vị trí user đến quán."""
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={user_lat},{user_lon}"
        f"&destination={dest_lat},{dest_lon}"
        f"&travelmode=driving"
    )


def generate_grab_food_deeplink(
    lat: float | None = None,
    lon: float | None = None,
    keyword: str = "",
) -> str:
    """
    Tạo deep link đến GrabFood search.

    Trên mobile sẽ mở app Grab, trên web sẽ mở trang GrabFood.
    """
    base = "https://food.grab.com/vn/vi/"
    if keyword:
        return f"{base}?search={quote(keyword)}"
    return base


def generate_shopee_food_deeplink(
    lat: float | None = None,
    lon: float | None = None,
    keyword: str = "",
) -> str:
    """
    Tạo deep link đến ShopeeFood search.
    """
    base = "https://shopeefood.vn/"
    if keyword:
        return f"{base}ha-noi/food/deals?q={quote(keyword)}"
    return base


def attach_map_links(
    scored_item: dict,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> dict:
    """
    Gắn Google Maps URL + app deeplinks vào scored item.
    Modifies dict in-place và return nó.
    """
    r_lat = scored_item.get("restaurant_lat")
    r_lon = scored_item.get("restaurant_lon")
    name = scored_item.get("restaurant_name", "")
    address = scored_item.get("restaurant_address", "")

    scored_item["google_maps_url"] = generate_google_maps_url(
        name, r_lat, r_lon, address
    )

    if user_lat is not None and user_lon is not None and r_lat and r_lon:
        scored_item["directions_url"] = generate_directions_url(
            user_lat, user_lon, r_lat, r_lon
        )

    keyword = scored_item.get("item_name", "")
    scored_item["grab_food_url"] = generate_grab_food_deeplink(keyword=keyword)
    scored_item["shopee_food_url"] = generate_shopee_food_deeplink(keyword=keyword)

    return scored_item


async def reverse_geocode(lat: float, lon: float) -> str:
    """
    Chuyển đổi tọa độ (lat, lon) thành địa chỉ cụ thể bằng tiếng Việt.
    Dùng Geoapify Reverse Geocoding API.
    """
    cache_key = f"address:{round(lat, 4)}:{round(lon, 4)}"
    cached = address_cache.get(cache_key)
    if cached is not None:
        return cached

    if has_key("GEOAPIFY_API_KEY"):
        try:
            url = "https://api.geoapify.com/v1/geocode/reverse"
            params = {
                "lat": lat,
                "lon": lon,
                "apiKey": GEOAPIFY_API_KEY,
                "lang": "vi",
            }
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if data.get("features"):
                    props = data["features"][0]["properties"]
                    name = props.get("name", "")
                    addr = props.get("address_line2", "") or props.get("formatted", "")
                    
                    if name and name not in addr:
                        formatted = f"{name}, {addr}"
                    else:
                        formatted = addr

                    # Loại bỏ phần ", Việt Nam" thừa nếu có
                    if formatted.endswith(", Việt Nam"):
                        formatted = formatted[:-10]
                    
                    if formatted:
                        address_cache.set(cache_key, formatted)
                        return formatted
        except Exception:
            pass

    return f"Khu vực ({lat:.4f}, {lon:.4f})"
