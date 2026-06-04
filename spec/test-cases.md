# Test Cases và bằng chứng kiểm thử

**Ngày kiểm thử gần nhất:** 04/06/2026

## Automated tests

Chạy từ `codebase/ai-food-agent`:

```powershell
pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Kết quả:

```text
76 passed
```

Coverage chức năng gồm:

- Guardrails: prompt injection, out-of-scope, sanitize input và history.
- Dị ứng và dietary filtering.
- Scoring, backup selection và correction.
- Cache theo GPS và map/direction links.
- Geoapify mapping, menu/giá ước tính và USDA normalization.
- API `/api/context`, `/api/chat` và hành vi thiếu GPS.

## Manual/API smoke tests

| Case | Input/thiết lập | Kết quả thực tế |
|---|---|---|
| Không có GPS | `GET /api/context` không truyền tọa độ | `location.available=false`, `lat/lon/city=null`; không trả vị trí mặc định như vị trí user |
| Hỏi quán gần khi thiếu GPS | `Quán nào gần tôi nhất?` | Agent trả yêu cầu bật quyền Location, `location_required=true`, không có suggestions |
| Có GPS | `21.0285, 105.8542` | Reverse geocode trả khu vực `79 Phố Đinh Tiên Hoàng, Hà Nội` |
| Quán gần GPS mẫu | Tìm 3 quán gần tọa độ trên | Geoapify trả Quán 4F `0.1 km`, Cơm Văn Phòng `0.2 km`, Phở Thìn Bờ Hồ `0.2 km` tại thời điểm kiểm thử |
| Multi-turn | Gợi ý quán, sau đó hỏi quán đầu tiên cách bao xa | Agent nhớ quán đầu tiên và trả địa chỉ + khoảng cách |
| Correction | `Đổi món khác đi` | Món/quán đang hiển thị được ghi vào rejected list và không lặp trong lần chọn mới |

## Failure cases để demo

| Failure | Kỳ vọng |
|---|---|
| User từ chối GPS | Không bịa vị trí/khoảng cách; hướng dẫn bật quyền |
| Câu hỏi ngoài phạm vi | Từ chối thân thiện và quay lại phạm vi gợi ý đồ ăn |
| Prompt injection | Không đổi vai trò/system prompt |
| API ngoài lỗi | Fallback/cache/mock có nhãn, không crash |
| Menu/giá không có từ Places | Dữ liệu thay thế được gắn nhãn ước tính |

## Bằng chứng còn cần bổ sung trước demo

- Screenshot happy path.
- Screenshot thiếu GPS.
- Screenshot correction path.
- Video backup ngắn nếu mạng/API ngoài không ổn định.
