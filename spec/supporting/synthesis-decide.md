# Toolkit — Từ Evidence Đến Build Slice

**Nhóm:** Dương Đức Cường (2A202600794), Đinh Hoàng Nam (2A202600884), Bùi Hoàng Sơn (2A202600925), Ngô Minh Khánh (2A202600953), Bùi Như Kiệt (2A202600895)  
**Ngày:** 03/06/2026

---

## 1. Gom evidence thành cụm

Gom theo **workflow/pain**, không gom theo tên feature.

| Cụm | Evidence thuộc về |
|---|---|| **"Gợi ý sai context thời gian"** | Test #1: gợi ý lẩu buổi sáng. Test #7: gợi ý quán đóng cửa đêm khuya. Test #10: quán ngưng nhận đơn trên ShopeeFood dù Maps báo mở. |
| **"Gợi ý không theo thời tiết"** | Test #2: trời mưa lạnh gợi ý trà sữa, salad. DoorDash DeepRed đã giải quyết bằng Weather API. |
| **"Không hiểu cảm xúc/mood user"** | Test #6: buồn/stress muốn comfort food nhưng phải tự tìm. Uber Eats đã có "Cravings" mood filter. |
| **"Search không hiểu natural language"** | Test #3: "healthy gần đây dưới 50k" → kết quả lộn xộn. Phải tách 3 bước. |
| **"Thiếu thông tin dinh dưỡng"** | Test #4: không biết món bao nhiêu calo. Nutritionix API có thể giải quyết. |
| **"Gợi ý thiên vị quảng cáo"** | Test #5: "Gợi ý cho bạn" chủ yếu là paid promotion. Review public xác nhận. |
| **"Bỏ qua khoảng cách và phí ship"** | Test #8: gợi ý món rẻ nhưng quán quá xa khiến phí ship làm đội tổng tiền vượt budget. |
| **"Trải nghiệm đặt hàng đứt gãy"** | Test #9: phải tự nhớ và gõ lại tên quán từ chatbot sang ShopeeFood thủ công. |

---

## 2. Viết insight

```text
User trẻ Việt Nam dùng food delivery hàng ngày
không chỉ cần một danh sách quán ăn gần đây.
Họ thật ra cần một trợ lý ăn uống HIỂU NGỮ CẢNH CON NGƯỜI VÀ THỰC TẾ CHI PHÍ,
vì evidence từ 10 bài test cho thấy:
  - Phần lớn pain đều liên quan đến app gợi ý ĐÚNG MÓN nhưng SAI CONTEXT.
  - App không xét thời gian (sáng/tối), thời tiết (mưa/nắng), cảm xúc (buồn/vui).
  - Không cảnh báo tổng chi phí thực tế (bao gồm phí ship phát sinh theo khoảng cách).
  - Đứt gãy trải nghiệm khi bắt user tự gõ lại tên quán để đặt hàng.
  - Rủi ro quán đã đóng cửa/ngưng nhận đơn trên app giao hàng dù Maps báo mở.
Vấn đề cốt lõi không phải app thiếu data quán ăn — ShopeeFood có hàng nghìn quán.
Vấn đề là app "KHÔNG HIỂU BẠN ĐANG CẦN GÌ LÚC NÀY VÀ TRẢI NGHIỆM ĐẶT HÀNG CHƯA LIỀN MẠCH".
```

---

## 3. Viết opportunity

```text
Cơ hội là dùng AI agent kết hợp nhiều nguồn context để gợi ý phù hợp và tối ưu luồng đặt:
  - Thời tiết real-time (Weather API) → mưa lạnh = món ấm nóng, nắng nóng = món thanh mát.
  - Thời gian trong ngày → phân phối nhóm món ăn theo bữa (sáng/trưa/chiều/đêm).
  - Cảm xúc user (chatbot hỏi mood) → stress = comfort food ngọt/cay, khỏe khoắn = món mới.
  - Budget thực tế → tính toán khoảng cách từ Google Maps và tự động cộng phí ship ước tính để lọc tổng tiền chính xác.
  * Backup rủi ro đóng cửa → Gợi ý 1 món ăn đi kèm 2-3 quán gần nhất có bán món đó.
  * Tối ưu UX đặt hàng → Cung cấp nút copy nhanh tên quán và link search trực tiếp.
  - Dinh dưỡng (Nutritionix) → cung cấp thông tin calo ước tính cho mỗi món đề xuất.
giúp user ra quyết định "ăn gì" trong 30 giây thay vì lướt 15 phút, tăng độ tin cậy và tiện lợi.
```

---

## 4. Chọn build slice

Build slice đã qua 5 câu hỏi kiểm tra:

| Câu hỏi | Đánh giá |
|---|---|
| **User cụ thể chưa?** | ✅ Sinh viên / dân văn phòng trẻ (18-28), dùng food delivery hàng ngày, hay phân vân "ăn gì?", quan tâm sức khoẻ + budget thực tế + mood. |
| **Task đủ hẹp chưa?** | ✅ Một task: user mở chatbot → nhập mood/context hoặc AI tự detect (thời tiết, thời gian) → AI gợi ý 2-3 món kèm quán + calo + giá đã tính ship + nút copy và quán backup → user chọn. |
| **AI decision rõ chưa?** | ✅ AI quyết định: (1) context nào quan trọng nhất lúc này? (2) gợi ý món gì phù hợp? (3) quán nào gần + đang mở cửa thực tế? → Augmentation: AI gợi ý, user chọn. |
| **Failure path rõ chưa?** | ✅ Case 1: AI đoán mood sai (buồn gợi ý salad). Case 2: AI tính ship sai hoặc gợi ý quán đóng cửa ngưng nhận đơn → Cần gợi ý backup + cho user sửa preference. |
| **Có evidence không?** | ✅ 10 self-use observations + review public (vtv.vn, shopeefood.vn) + 3 competitor analogs (DoorDash, Uber Eats, Cleo AI). |

---

## 5. Quyết định: giữ, giảm scope, hay đổi hướng?

| Tình huống | Quyết định |
|---|---|
| Evidence yếu? | Không — 10 self-use + public review + 3 competitor analogs. |
| Ý tưởng quá rộng? | Ban đầu có → đã cắt xuống 1 flow gợi ý theo context. Thêm công thức tính ship ước tính + copy shortcut để tăng tính thực tế cho prototype mà không tăng quá nhiều độ phức tạp. |
| AI không cần thiết? | Cần — kết hợp thời tiết + mood + thời gian + vị trí + dinh dưỡng cần intelligence. |
| Rủi ro cao? | Trung bình — chọn augmentation. Rủi ro chính: gợi ý sai mood hoặc quán đóng cửa. |
| Demo được trong 1 ngày? | ✅ Có — chatbot prototype + mock/real API calls. |

**Quyết định: GIỮ build slice, đã giảm scope vừa đủ.**

---

## 6. Câu chốt cuối

```text
Dựa trên evidence từ 10 bài test thực tế với ShopeeFood
(đặc biệt: gợi ý lẩu buổi sáng, salad ngày mưa lạnh, phí ship quá cao vượt budget,
gợi ý quán đóng cửa và đứt gãy UX khi phải gõ lại tên quán),
nhóm sẽ build prototype AI agent gợi ý món ăn theo ngữ cảnh cho sinh viên/dân văn phòng trẻ,
để giải quyết pain "app gợi ý đúng món nhưng sai context và chi phí thực tế",
bằng cách AI kết hợp thời tiết (Weather API) + thời gian + mood (chatbot)
+ budget thực tế (cộng thêm phí ship dựa trên khoảng cách) + vị trí (Google Maps) + quán backup
+ nút copy nhanh tên quán + dinh dưỡng (Nutritionix),
và sẽ test failure path: AI đoán mood sai hoặc gợi ý quán đã đóng cửa/ship quá đắt.
```PI calls real-time. |

**Quyết định: GIỮ build slice, đã giảm scope vừa đủ.**

---

## 6. Câu chốt cuối

```text
Dựa trên evidence từ 7 bài test thực tế với ShopeeFood
(đặc biệt: app gợi ý lẩu buổi sáng, salad trời mưa lạnh,
quán đóng cửa đêm khuya — tất cả là SAI CONTEXT, không sai data),
nhóm sẽ build prototype AI agent gợi ý món ăn theo ngữ cảnh,
cho sinh viên/dân văn phòng trẻ hay phân vân "ăn gì?",
để giải quyết pain "app gợi ý đúng món nhưng sai context",
bằng cách AI kết hợp thời tiết (Weather API) + thời gian + mood (chatbot)
+ budget + health + vị trí (Google Maps) + dinh dưỡng (Nutritionix),
và sẽ test failure path: AI đoán mood sai → gợi ý ngược hoàn toàn
với kỳ vọng user (buồn → salad, vui → lẩu cay) → user frustrate.
```

---

## 7. Backlog

Những thứ **không build trong Day 06**:

- Tích hợp trực tiếp với ShopeeFood API (không có public API, cần đối tác).
- Đặt đơn trong chatbot (chỉ gợi ý, user tự đặt trên ShopeeFood).
- Học từ lịch sử đặt hàng user (cần data thật, chưa có).
- Recommendation cộng đồng ("bạn bè bạn hay ăn gì?") — cần social graph.
- OCR menu quán ăn để phân tích dinh dưỡng tự động.
