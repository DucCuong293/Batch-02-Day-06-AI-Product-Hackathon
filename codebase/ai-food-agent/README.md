# Yumi - AI Food Agent Prototype

Yumi là trợ lý AI gợi ý món ăn theo ngữ cảnh cho sinh viên và dân văn phòng tại Hà Nội. Prototype kết hợp hội thoại tiếng Việt với GPS, thời tiết, thời gian, mood, budget, khoảng cách, phí ship ước tính và dinh dưỡng.

## Chạy ứng dụng

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item .env.example .env
# Điền API keys vào .env
cd backend
python main.py
```

Mở `http://localhost:8000` và chọn **Allow/Cho phép** khi trình duyệt hỏi quyền vị trí.

> Trình duyệt chỉ cho phép Geolocation trên `localhost` hoặc HTTPS. Nếu chưa có GPS, Yumi không dùng tọa độ mặc định như vị trí người dùng và sẽ yêu cầu bật quyền khi câu hỏi phụ thuộc vị trí.

## API keys

| Biến | Vai trò | Bắt buộc |
|---|---|---|
| `OPENAI_API_KEY` | LLM chính | Chọn OpenAI hoặc Gemini |
| `GEMINI_API_KEY` | LLM thay thế | Chọn OpenAI hoặc Gemini |
| `OPENWEATHERMAP_API_KEY` | Thời tiết thật | Không; có fallback |
| `GEOAPIFY_API_KEY` | Tìm quán và reverse geocoding | Không; có mock fallback |
| `USDA_FDC_API_KEY` | Dinh dưỡng FoodData Central | Không; có fallback |
| `GOOGLE_PLACES_API_KEY` | Places tùy chọn, cần Billing | Không |

Sao chép `.env.example` thành `.env`. Không commit `.env` hoặc key thật.

## Kiến trúc

```text
Frontend HTML/CSS/JS
        |
        v
FastAPI: /api/context + /api/chat
        |
        +-- LLM Agent: OpenAI / Gemini
        +-- Guardrails: injection, out-of-scope, allergy, validation
        +-- Geoapify: quán gần + địa chỉ
        +-- OpenWeatherMap: thời tiết
        +-- USDA: dinh dưỡng
        +-- Scoring + shipping + backup selection
```

Scoring:

```text
score = 0.30 food_match
      + 0.25 delivery_time
      + 0.20 rating
      + 0.15 budget_fit
      + 0.10 reliability
```

## Chức năng chính

- Chat tiếng Việt và hội thoại nhiều lượt.
- Hiểu món cụ thể, budget, mood, healthy/comfort, dị ứng và correction.
- Luôn xin GPS mới khi mở app; không giả định vị trí hiện tại.
- Tìm quán gần qua Geoapify, tính khoảng cách và phí ship ước tính.
- Dùng weather/time để điều chỉnh gợi ý.
- Dinh dưỡng USDA được ghi rõ theo `/100g`.
- Một lựa chọn chính và các backup an toàn/giao nhanh/tiết kiệm.
- Nhãn minh bạch cho menu, giá, ship và dữ liệu ước tính.
- Prompt-injection guardrail, out-of-scope guardrail, rate limiting và input validation.

## Kiểm thử

```powershell
pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Kết quả gần nhất: **76 passed**.

## Giới hạn

- Geoapify không cung cấp menu/giá món hoặc trạng thái nhận đơn của ShopeeFood; dữ liệu thay thế luôn được gắn nhãn ước tính.
- Phí ship và thời gian giao là ước tính, không phải báo giá giao dịch.
- Đặt món trực tiếp cần API đối tác chính thức; prototype để người dùng tự quyết định và đặt trên nền tảng gốc.
