# Yumi - Product SPEC

## 1. Vấn đề, người dùng và bằng chứng

**Người dùng chính:** sinh viên và dân văn phòng trẻ tại Hà Nội thường xuyên dùng ứng dụng giao đồ ăn, hay phân vân "ăn gì?", quan tâm budget, sức khỏe và thời gian giao.

**Pain statement:** các ứng dụng giao đồ ăn có nhiều dữ liệu quán nhưng thường đưa đề xuất sai ngữ cảnh. Người dùng vẫn phải tự lướt, lọc và so sánh vì danh sách gợi ý không hiểu đồng thời thời gian, thời tiết, tâm trạng, vị trí và tổng chi phí gồm phí ship.

### Bằng chứng của nhóm

- Nhóm tự dùng ShopeeFood và ghi nhận 10 điểm gãy: lẩu/buffet vào buổi sáng, salad/trà sữa lạnh khi trời mưa, tìm kiếm nhiều tiêu chí không chính xác, thiếu dinh dưỡng, quán đóng cửa, phí ship làm vượt budget và trạng thái quán lệch giữa nền tảng.
- Nguồn ngoài nhóm được ghi nhận trong evidence pack gồm phản hồi công khai về đề xuất thiên vị quảng cáo, bộ lọc dinh dưỡng chưa sâu và trải nghiệm tìm kiếm mất thời gian.
- Competitor analog: DoorDash dùng context vận hành; Uber Eats dùng nhóm craving; Cleo cho thấy hội thoại theo mood giúp trải nghiệm gần gũi hơn.

Chi tiết và nguồn đã thu thập: [`supporting/evidence-pack.md`](supporting/evidence-pack.md). Các nhận định chưa có link hoặc ảnh lưu kèm được xem là giả thuyết cần kiểm chứng thêm, không phải kết luận đã chứng minh.

## 2. Lát cắt để build

> Với một sinh viên/dân văn phòng đang không biết ăn gì, Yumi dùng AI để hiểu nhu cầu và ngữ cảnh hiện tại, chọn một món/quán chính cùng phương án dự phòng, rồi trả về lý do, khoảng cách, tổng chi phí và dinh dưỡng để người dùng quyết định.

### Trong scope

- Chat tiếng Việt, hiểu món, budget, mood, healthy/comfort và yêu cầu đổi.
- GPS hiện tại, thời tiết, thời gian, quán gần, khoảng cách và phí ship ước tính.
- Một lựa chọn chính và các phương án backup theo vai trò.
- Dinh dưỡng USDA và nhãn minh bạch cho dữ liệu ước tính.
- Happy, low-confidence, failure và correction paths.

### Ngoài scope

- Đặt đơn hoặc thanh toán thật trên ShopeeFood/GrabFood.
- Trạng thái nhận đơn và menu giao dịch real-time của nền tảng giao đồ ăn.
- Học sở thích dài hạn qua nhiều tài khoản/ngày.

## 3. AI Product Canvas

| Ô | Quyết định của nhóm |
|---|---|
| **Value** | Yumi giảm choice overload bằng cách kết hợp nhiều tín hiệu mà search/filter thông thường không xử lý tốt trong một lượt: ngôn ngữ tự nhiên, mood, weather, time, GPS, budget và dinh dưỡng. |
| **Trust** | Hiển thị khoảng cách, lý do, nguồn/quán và gắn nhãn giá/menu/phí ship/dinh dưỡng ước tính. Không có GPS thì yêu cầu cấp quyền thay vì dùng vị trí giả. Người dùng có thể đổi món/đổi quán và luôn tự đặt hàng trên app gốc. |
| **Feasibility** | FastAPI + frontend tĩnh đủ cho prototype một ngày. Geoapify, OpenWeatherMap và USDA có free tier; OpenAI/Gemini là phần có chi phí. Cache giảm số API call. Rủi ro lớn nhất là dữ liệu quán/menu không đồng bộ với nền tảng giao hàng. |
| **Tín hiệu học** | Trong phiên hiện tại, Yumi lưu mood, budget, dị ứng và món/quán bị từ chối để tránh lặp. Prototype chưa lưu dài hạn; bản production cần feedback store và consent rõ ràng. |

### Ngưỡng dừng/đổi hướng

- Nếu không thể xác minh GPS hoặc quán, không đưa ra khoảng cách/quán gần như sự thật.
- Nếu API nhà hàng không cung cấp menu/giá, tiếp tục gắn nhãn ước tính; không dùng dữ liệu đó để tự đặt đơn.
- Nếu độ trễ nhiều API làm flow không thể demo ổn định, dùng cache/mock có nhãn để giữ flow nhưng vẫn duy trì ít nhất một lời gọi AI thật.

## 4. Augment hay Automate?

Yumi chọn **augmentation**.

AI được phép hiểu yêu cầu, tổng hợp context, lọc/xếp hạng và giải thích lựa chọn. AI không được tự đặt món, tự thanh toán hoặc khẳng định dữ liệu ước tính là dữ liệu giao dịch thật. Con người giữ quyền chọn món, kiểm tra trạng thái trên app giao hàng và quyết định đặt đơn.

Lý do: khẩu vị mang tính chủ quan; giá/menu/trạng thái nhận đơn có thể lệch giữa Geoapify và nền tảng giao hàng; hành động đặt đơn có chi phí và khó hoàn tác hơn một gợi ý.

## 5. Bốn đường đi trải nghiệm

| Đường đi | Hành vi prototype |
|---|---|
| **Happy** | Người dùng cấp GPS và hỏi món theo context/budget. Agent gọi AI thật, tìm quán gần, xếp hạng và trả card có khoảng cách, tổng chi phí, dinh dưỡng và backup. |
| **AI không chắc** | Câu như "ăn gì cũng được" khiến Agent hỏi làm rõ hoặc đưa quick options thay vì tự tin đoán một nhu cầu cụ thể. |
| **AI sai / dữ liệu thiếu** | Thiếu GPS thì trả lời yêu cầu bật quyền; API lỗi có fallback/cache/mock được gắn nhãn; dữ liệu menu/giá/phí ship ước tính được hiển thị minh bạch. |
| **Người dùng sửa** | "Đổi món", "đổi quán", "không muốn healthy" cập nhật preference trong session, loại món/quán vừa bị từ chối và tạo gợi ý mới. |

## 6. Failure modes đáng lo nhất

### 6.1 Dùng sai hoặc giả định vị trí người dùng

- **Khi xảy ra:** trình duyệt từ chối GPS, GPS cũ hoặc tọa độ bị cache quá rộng.
- **Thiệt hại:** khoảng cách, phí ship và quán gần đều sai; giảm niềm tin.
- **Xử lý:** luôn xin GPS mới khi mở app; không lưu GPS vào session; thiếu GPS thì trả `location_required=true`; cache quán dùng tọa độ bốn chữ số thập phân.

### 6.2 Quán/menu/giá không phản ánh trạng thái giao hàng thật

- **Khi xảy ra:** Geoapify biết địa điểm nhưng không có menu giao dịch hoặc trạng thái "tạm ngưng nhận đơn" của ShopeeFood.
- **Thiệt hại:** người dùng không đặt được hoặc tổng tiền thực tế khác.
- **Xử lý:** gắn nhãn ước tính, cung cấp quán backup, để người dùng kiểm tra/đặt trên nền tảng gốc.

### 6.3 AI hiểu sai nhu cầu hoặc bị prompt injection

- **Khi xảy ra:** đầu vào mơ hồ, ngoài phạm vi hoặc cố thay đổi vai trò Agent.
- **Thiệt hại:** gợi ý không phù hợp, hội thoại mất kiểm soát.
- **Xử lý:** clarification, correction path, out-of-scope guardrail, prompt-injection detection, validation lịch sử và dị ứng.

## 7. Kế hoạch kiểm thử và bằng chứng demo

### Input bình thường

```text
Trời mưa, mình muốn ăn phở dưới 70k gần đây.
```

Kỳ vọng: Agent nhận context, tìm quán gần, trả lựa chọn chính + backup, khoảng cách và tổng chi phí.

### Input khó

```text
Quán nào gần tôi nhất?
```

Thực hiện khi chưa cấp GPS. Kỳ vọng: Agent không dùng vị trí mặc định và yêu cầu bật quyền vị trí.

### Input correction

```text
Không muốn ăn healthy đâu, đổi món khác đi.
```

Kỳ vọng: Agent ghi nhận correction, loại lựa chọn cũ và đưa lựa chọn mới.

Các case đã kiểm thử và kết quả thực tế được ghi trong [`test-cases.md`](test-cases.md). Automated suite hiện có **76 tests**.

## 8. Phân công

| Thành viên | Trách nhiệm | Phần có thể giải thích khi demo |
|---|---|---|
| Dương Đức Cường | Leader, evidence/SPEC, AI/backend/API integration, repo | Luồng Agent, API, guardrails, scoring, quyết định sản phẩm |
| Đinh Hoàng Nam | Prototype development, frontend/integration support | Giao diện, flow chat và tích hợp frontend-backend |
| Bùi Hoàng Sơn | Testing và QA | 4 paths, test cases, failure modes và hồi quy |
| Ngô Minh Khánh | Business/UX research | Painpoint, evidence, problem-solution fit |
| Bùi Như Kiệt | Demo script và tài liệu | Kịch bản trình bày, giới hạn và lessons learned |

## 9. Kiến trúc prototype

```text
Browser GPS + Chat UI
        |
        v
FastAPI /api/context + /api/chat
        |
        +--> LLM Agent: OpenAI hoặc Gemini
        +--> Geoapify: places + reverse geocoding
        +--> OpenWeatherMap: thời tiết
        +--> USDA FoodData Central: dinh dưỡng
        +--> Scoring + shipping + backup selection
```

Agent sử dụng dữ liệu thật khi key khả dụng và fallback có nhãn khi API ngoài không khả dụng. Google Places chỉ là tùy chọn; luồng chính sử dụng Geoapify.
