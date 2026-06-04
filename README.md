# Yumi - AI Food Agent

**Track:** Food & Local Delivery

**App tham khảo:** ShopeeFood

**Build slice:** AI gợi ý món và quán phù hợp với ngữ cảnh hiện tại của người dùng.

Yumi giúp sinh viên và dân văn phòng trả lời câu hỏi "ăn gì bây giờ?" bằng cách kết hợp hội thoại tự nhiên với thời tiết, thời gian, vị trí GPS, tâm trạng, ngân sách, khoảng cách, phí ship ước tính và dữ liệu dinh dưỡng. AI thu hẹp hàng nghìn lựa chọn xuống một quán chính cùng các phương án dự phòng; người dùng luôn giữ quyền quyết định cuối cùng.

## Thành viên và phân công

| Thành viên | Mã học viên | Phụ trách |
|---|---|---|
| Dương Đức Cường | 2A202600794 | Leader; tổng hợp evidence và SPEC; tích hợp AI/backend/API; quản lý repo |
| Đinh Hoàng Nam | 2A202600884 | Prototype development; hỗ trợ frontend và tích hợp API |
| Bùi Hoàng Sơn | 2A202600925 | Testing và QA; kiểm thử happy, low-confidence, failure, correction |
| Ngô Minh Khánh | 2A202600953 | Business/UX; nghiên cứu người dùng và problem-solution fit |
| Bùi Như Kiệt | 2A202600895 | Demo script, tài liệu và hỗ trợ quản lý bản nộp |

## Giá trị được chứng minh

- Hiểu yêu cầu nhiều tiêu chí bằng tiếng Việt: món, budget, healthy/comfort và mood.
- Tự xin GPS khi mở app; không giả định vị trí nếu người dùng chưa cấp quyền.
- Tìm quán thật gần người dùng qua Geoapify và tính khoảng cách.
- Dùng thời tiết thật từ OpenWeatherMap để tạo ngữ cảnh.
- Tra dinh dưỡng qua USDA FoodData Central.
- Xếp hạng quán theo độ phù hợp, giao nhanh, rating, budget và độ tin cậy.
- Cho phép đổi món/đổi quán; không lặp lại lựa chọn vừa bị từ chối.
- Chặn prompt injection, câu hỏi ngoài phạm vi và xử lý dữ liệu/API thiếu.

## Cấu trúc repo

```text
.
├── README.md
├── hackathon-rules.md
├── spec/
│   ├── spec.md
│   ├── demo-script.md
│   ├── test-cases.md
│   └── supporting/
│       ├── evidence-pack.md
│       ├── synthesis-decide.md
│       └── thin-spec-day5.md
└── codebase/
    ├── README.md
    └── ai-food-agent/
        ├── backend/
        ├── frontend/
        ├── tests/
        └── .env.example
```

## Chạy prototype

Yêu cầu: Python 3.11+.

```powershell
cd codebase/ai-food-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item .env.example .env
# Điền API keys vào .env
cd backend
python main.py
```

Mở `http://localhost:8000`, sau đó chọn **Allow/Cho phép** khi trình duyệt hỏi quyền vị trí. Geolocation chỉ hoạt động trên `localhost` hoặc HTTPS.

## API và công cụ

| Nhóm | Công cụ |
|---|---|
| AI thật | OpenAI GPT-4o-mini hoặc Gemini |
| Nhà hàng/vị trí | Geoapify Places + Reverse Geocoding |
| Thời tiết | OpenWeatherMap |
| Dinh dưỡng | USDA FoodData Central |
| Backend | FastAPI, Pydantic, HTTPX, SlowAPI |
| Frontend | HTML, CSS, JavaScript |
| Kiểm thử | Pytest |

Google Places là tích hợp tùy chọn; luồng chính sử dụng Geoapify để không phụ thuộc Google Billing. Không commit `.env` hoặc API key thật.

## Kiểm thử

```powershell
cd codebase/ai-food-agent
pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Kết quả gần nhất: **76 tests passed**.

## Tài liệu demo

- [SPEC sản phẩm](spec/spec.md)
- [Kịch bản demo 5 phút](spec/demo-script.md)
- [Test cases và bằng chứng kiểm thử](spec/test-cases.md)
- [Evidence pack Day 5](spec/supporting/evidence-pack.md)
