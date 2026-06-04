# 🍜 Yumi — AI Food Agent

**Context-Aware Food Recommendation Prototype**

> Trợ lý AI gợi ý món ăn thông minh theo ngữ cảnh: thời tiết, tâm trạng, budget, dinh dưỡng.
> Dành cho sinh viên và dân văn phòng tại Hà Nội.

**Nhóm:** Dương Đức Cường (2A202600794), Đinh Hoàng Nam, Bùi Hoàng Sơn, Ngô Minh Khánh, Bùi Như Kiệt
**Track:** C — Food & Local Delivery | **App tham khảo:** ShopeeFood

---

## 🚀 Cài đặt & Chạy

### 1. Clone & setup

```bash
cd ai-food-agent
pip install -r backend/requirements.txt
```

### 2. Cấu hình API keys

```bash
cp .env.example .env
# Mở .env và điền API keys (xem hướng dẫn bên dưới)
```

### 3. Chạy server

```bash
cd backend
python main.py
```

Mở trình duyệt: **http://localhost:8000**

---

## 🔑 API Keys

| API | Đăng ký | Free Tier |
|-----|---------|-----------|
| **OpenAI** | [platform.openai.com](https://platform.openai.com) | Pay-per-use (~$0.15/1M tokens cho gpt-4o-mini) |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com) | 15 RPM free |
| **OpenWeatherMap** | [openweathermap.org](https://openweathermap.org) | 60 calls/phút miễn phí |
| **Geoapify Places** | [myprojects.geoapify.com](https://myprojects.geoapify.com/) | 3,000 credits/ngày |
| **USDA FoodData Central** | [fdc.nal.usda.gov/api-key-signup](https://fdc.nal.usda.gov/api-key-signup/) | 1,000 requests/giờ |
| **Google Places (tùy chọn)** | [console.cloud.google.com](https://console.cloud.google.com) | Cần bật Billing |

> **Lưu ý:** Prototype chạy được **không cần API key** — sẽ tự dùng mock data demo.

---

## 🏗️ Kiến trúc

```
Frontend (HTML/CSS/JS) ←→ Backend (FastAPI Python)
                              ├── LLM Agent (OpenAI / Gemini)
                              ├── Weather Service (OpenWeatherMap)
                              ├── Places Service (Geoapify, Google fallback)
                              ├── Nutrition Service (USDA FoodData Central)
                              ├── Scoring Engine (5 tiêu chí)
                              └── Shipping Calculator
```

### Scoring Algorithm

```
score = 0.30 × food_match + 0.25 × delivery_time + 0.20 × rating + 0.15 × budget_fit + 0.10 × reliability
```

### Backup Selection
- 🏆 **Quán chính:** Score cao nhất tổng thể
- 🛡️ **An toàn:** Cùng loại món, rating ổn (phòng quán chính hết hàng)
- ⚡ **Giao nhanh:** Thời gian giao ngắn nhất
- 💰 **Tiết kiệm:** Tổng giá thấp nhất

---

## 📋 Tính năng

- ✅ Chat NLP tự nhiên tiếng Việt
- ✅ Detect tâm trạng (vui/buồn/stress/mệt) + nút bấm nhanh
- ✅ Thời tiết real-time → gợi ý phù hợp
- ✅ Phân loại bữa ăn theo giờ (sáng/trưa/chiều/tối/đêm)
- ✅ Tính phí ship ước tính (15k/2km + 5k/km)
- ✅ Ước tính calo cho mỗi món
- ✅ Quán backup theo vai trò (an toàn/nhanh/rẻ)
- ✅ Nút Copy tên quán → paste vào ShopeeFood
- ✅ Override buttons: Đổi món, Ngọt ngào, Cay nồng, Thanh đạm
- ✅ 4 Paths: Happy, Low-confidence, Failure, Correction
- ✅ GPS trình duyệt, fallback về Gia Lâm khi người dùng từ chối định vị
- ✅ Ghi nhớ phiên chat qua refresh bằng `sessionStorage`
- ✅ Loại món/quán vừa bị từ chối khỏi lần gợi ý tiếp theo
- ✅ Menu/giá ước tính cho dữ liệu Places được gắn nhãn minh bạch
- ✅ Dinh dưỡng USDA thật được hiển thị rõ theo chuẩn `/100g`

---

## 🧪 Kiểm thử

```bash
pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Test hồi quy bao phủ yêu cầu món cụ thể, correction, menu ước tính từ Places,
chuẩn hóa dữ liệu USDA và lựa chọn backup cùng nhóm món.

> Geoapify và Google Places không cung cấp menu/giá món. Khi dùng Places thật, Yumi tạo
> menu tham chiếu để scoring không bị rỗng và luôn hiển thị nhãn **ước tính**.

## Giới hạn tích hợp bên ngoài

- Đặt món trực tiếp cần API đối tác chính thức từ nền tảng giao đồ ăn; phiên bản
  hiện tại vẫn hỗ trợ copy tên quán để người dùng tự tìm và đặt.
- Giá món, phí ship và thời gian giao chỉ trở thành dữ liệu giao dịch thật khi có
  API menu/đơn hàng từ đối tác. Yumi luôn gắn nhãn ước tính cho dữ liệu thay thế.
