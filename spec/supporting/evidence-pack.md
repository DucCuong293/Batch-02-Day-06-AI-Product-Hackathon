# Template — Evidence Pack

**Nhóm:** Dương Đức Cường (2A202600794), Đinh Hoàng Nam (2A202600884), Bùi Hoàng Sơn (2A202600925), Ngô Minh Khánh (2A202600953), Bùi Như Kiệt (2A202600895)  
**Ngày:** 03/06/2026

---

## 1. Nhóm và track

**Tên nhóm:** Nhóm Cường — 5 thành viên  
**Track:** C — Food & Local Delivery  
**Product/app đã chọn:** ShopeeFood  
**Build slice đang nghĩ:** Prototype AI agent gợi ý món ăn theo ngữ cảnh (thời tiết, cảm xúc, thời gian, budget, sức khoẻ) bằng cách kết hợp API thời tiết + Google Maps Places + Nutritionix — thay vì gợi ý chung chung / quảng cáo như ShopeeFood hiện tại.

---

## 2. Self-use evidence

Cả nhóm tự dùng ShopeeFood và ghi lại điểm gãy.

| # | Observation | Path liên quan | Điều học được |
|---|---|---|---|
| 1 | Buổi sáng mở app nhưng ShopeeFood gợi ý lẩu, buffet — món không phù hợp buổi sáng. Không có filter "bữa sáng". | **Failure** — Gợi ý không theo ngữ cảnh thời gian. | App chỉ gợi ý theo quảng cáo/popularity, không xét thời điểm trong ngày. |
| 2 | Trời mưa lạnh muốn ăn phở/cháo nóng nhưng app gợi ý trà sữa, salad. Phải tự search "phở" rồi lọc thủ công. | **Failure** — Gợi ý không theo thời tiết. | App không tích hợp dữ liệu thời tiết. User phải tự biết mình muốn gì rồi search keyword. |
| 3 | Tìm "quán ăn healthy gần đây dưới 50k" — search không hiểu câu ngữ cảnh, trả kết quả lộn xộn. | **Failure** — Search/filter yếu, không hiểu natural language. | Phải tách thành nhiều bước: search "healthy" → lọc giá → lọc khoảng cách. UX tệ. |
| 4 | Không biết món nào bao nhiêu calo. Muốn ăn ít calo nhưng app không có thông tin dinh dưỡng. | **Low-confidence** — Thiếu data dinh dưỡng hoàn toàn. | User quan tâm sức khoẻ không được hỗ trợ. Phải tự Google "phở bao nhiêu calo" riêng. |
| 5 | Gợi ý chủ yếu là quán đang chạy quảng cáo — không rõ đây là gợi ý tốt thật hay paid promotion. | **Low-confidence** — Ranh giới gợi ý vs quảng cáo mờ. | User mất niềm tin vào "Gợi ý cho bạn". Giống pain Moni (tư vấn vs quảng bá). |
| 6 | Khi buồn/stress muốn ăn comfort food (mì cay, trà sữa, kem) nhưng phải tự search. App không hiểu mood. | **Failure** — App không hỗ trợ context cảm xúc. | Đây là nhu cầu thật: "tôi buồn, gợi ý gì ăn cho vui?" — app delivery chưa ai giải quyết. |
| 7 | Đêm khuya (23h) app vẫn gợi ý quán đã đóng cửa → đặt không được → frustrating. | **Failure** — Gợi ý quán đã đóng cửa. | App không sync real-time giờ hoạt động của quán vào danh sách gợi ý. |
| 8 | Tìm món ăn dưới 50k, AI gợi ý món 45k ngon nhưng quán cách 5km → phí ship thực tế 25k (tổng 70k) vượt budget nghiêm trọng. | **Failure** — Gợi ý vượt budget thực tế do bỏ qua khoảng cách và phí ship. | Gợi ý budget phải bao gồm cả ước tính phí ship dựa trên khoảng cách. |
| 9 | Sau khi AI gợi ý, phải tự gõ thủ công lại tên quán trên ShopeeFood → trải nghiệm đứt gãy, dễ gõ sai. | **Failure** — Luồng trải nghiệm từ chatbot sang đặt hàng bị gãy. | Chatbot cần hỗ trợ nút copy tên quán nhanh hoặc deep-link search. |
| 10 | Gợi ý quán cơm mở cửa trên Google Maps nhưng khi mở ShopeeFood thực tế quán ghi "Tạm ngưng nhận đơn". | **Failure** — Trạng thái đóng/mở cửa giữa các nền tảng bị lệch nhau. | Cần gợi ý món ăn kèm danh sách 2-3 quán backup gần đó thay vì chỉ gợi ý 1 quán duy nhất. |

---

## 3. User / review / social evidence

| Quote / review / observation | Nguồn | User là ai? | Pain/failure mode |
|---|---|---|---|
| "Thuật toán tập trung quá mức vào các nhà hàng đang chạy quảng cáo hoặc chuỗi lớn, thay vì quán phù hợp sở thích cá nhân." | vtv.vn — Đánh giá ShopeeFood Knowledge Graph AI | Người dùng ShopeeFood nói chung | Failure — Gợi ý thiên vị quảng cáo, không cá nhân hoá thật. |
| "Bộ lọc chưa đủ sâu để phân loại theo nhu cầu khắt khe (chế độ dinh dưỡng, định lượng thực tế)." | shopeefood.vn — review tổng hợp | User có nhu cầu dinh dưỡng | Low-confidence — filter thiếu, user tự lọc thủ công. |
| "Trải nghiệm tìm kiếm chưa tối ưu, khách hàng mất nhiều thời gian tìm được món ưng ý." | shopeefood.vn — phản hồi người dùng | User bận rộn (dân văn phòng, sinh viên) | Failure — choice overload, search không smart. |
| "Đánh giá '5 sao' đôi khi không phản ánh thực tế vì review ảo và quảng cáo quá đà." | Tổng hợp từ review cộng đồng, shapo.io | User muốn tìm quán chất lượng thật | Low-confidence — mất tin cậy vào hệ thống đánh giá. |

---

## 4. Competitor / analog evidence

| App / mô hình tham khảo | Họ xử lý task này thế nào? | Pattern học được | Có áp dụng trong 1 ngày không? |
|---|---|---|---|
| **DoorDash (Mỹ)** — hệ thống DeepRed | AI dùng thời tiết + traffic + demand để gợi ý quán giao nhanh, điều chỉnh phí theo real-time. | Context-aware recommendation: kết hợp nhiều nguồn data (thời tiết, thời gian, traffic). | Có — prototype dùng Weather API + Google Maps. |
| **Uber Eats — "Cravings" feature** | Cho user chọn mood ("healthy", "comfort", "quick bite") rồi filter kết quả. | Mood-based filter đơn giản nhưng hiệu quả, giảm choice overload. | Có — prototype cho user chọn mood → AI filter. |
| **Cleo AI (Fintech UK)** | Chatbot hỏi user "How are you feeling?" rồi điều chỉnh tone + gợi ý. | Conversational AI hiểu ngữ cảnh cảm xúc qua chat. | Có — prototype chatbot hỏi mood + gợi ý. |

---

## 5. Evidence -> Insight

```text
Evidence nổi bật nhất:
1. ShopeeFood gợi ý lẩu buổi sáng, salad trời mưa, quán đóng cửa đêm khuya.
2. Search không hiểu "healthy gần đây dưới 50k" — phải tách nhiều bước.
3. Không có thông tin dinh dưỡng trên bất kỳ món nào.
4. Gợi ý thiên vị quảng cáo thay vì cá nhân hoá thật.
5. User buồn/stress muốn comfort food nhưng phải tự tìm.
6. Khoảng cách xa làm phát sinh phí ship cao khiến tổng đơn vượt budget của user.
7. Đứt gãy trải nghiệm khi phải copy/gõ thủ công tên quán từ chatbot sang ShopeeFood.
8. Quán hiển thị mở cửa nhưng thực tế trên ShopeeFood ngưng nhận đơn hoặc hết hàng.

Insight:
User trẻ Việt Nam dùng food delivery không chỉ cần một danh sách quán.
Họ thật ra cần một trợ lý ăn uống hiểu ngữ cảnh:
  - Bây giờ là sáng hay tối? Trời mưa hay nắng?
  - User đang vui, buồn, hay stress?
  - Budget thực tế là bao nhiêu (gồm cả phí ship dựa trên khoảng cách)?
  - Muốn healthy hay comfort? Có phương án quán backup hay không?
vì evidence cho thấy phần lớn pain đều liên quan đến
"app gợi ý ĐÚNG MÓN nhưng SAI CONTEXT" — không sai về data,
sai về hiểu ngữ cảnh con người.

Opportunity:
AI có thể giúp bằng cách kết hợp context thời tiết (Weather API)
+ thời gian + cảm xúc user (chatbot hỏi mood)
+ budget thực tế (bao gồm ước tính phí ship từ khoảng cách quán)
+ vị trí (Google Maps Places) để lọc quán gần nhất đang mở cửa
+ cung cấp 2-3 quán backup để tránh quán chính ngưng nhận đơn
+ cung cấp nút copy nhanh tên quán
+ thông tin dinh dưỡng (Nutritionix)
để gợi ý món phù hợp ngữ cảnh thay vì gợi ý chung chung.
```

---

## 6. Evidence đổi SPEC như thế nào?

- [x] Đổi user chính. → User trẻ (sinh viên, dân văn phòng) dùng food delivery hàng ngày, hay phân vân "ăn gì".
- [x] Đổi pain statement. → Pain không phải "app lỗi" mà là "app gợi ý đúng món nhưng sai context".
- [x] Đổi build slice. → AI agent gợi ý món theo ngữ cảnh (thời tiết + mood + thời gian + budget kèm ship + backup quán + copy shortcut).
- [x] Đổi Auto/Aug decision. → Augmentation: AI gợi ý 2-3 option, user chọn.
- [x] Đổi 4 paths. → Thêm low-confidence path khi AI không chắc mood user.
- [x] Đổi failure mode. → AI gợi ý sai mood (user buồn nhưng gợi ý healthy salad thay vì comfort food) hoặc phí ship vượt budget.
- [x] Đổi owner/test plan. → Chia 5 người: research, SPEC, prototype, test, demo.

Ghi rõ 1-2 thay đổi quan trọng:

```text
Trước evidence, nhóm định build "chatbot tìm quán ăn gần đây".
Sau evidence, nhóm nhận ra pain thật không phải "tìm quán"
  mà là "chọn món phù hợp LÚC NÀY, VỚI TÂM TRẠNG NÀY, THỜI TIẾT NÀY, VÀ CHI PHÍ THỰC TẾ NÀY".
  Đổi build slice thành context-aware food recommendation agent
  kết hợp Weather API + mood input + Google Maps + Nutritionix + công thức tính phí ship + quán backup + nút copy nhanh.
Lý do: Các pain points đều liên quan đến sai context và chi phí thực tế phát sinh (phí ship), không chỉ là thiếu data.
```
