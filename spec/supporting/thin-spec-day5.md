# Template — Thin SPEC Cuối Day 05

**Học viên:** Dương Đức Cường — 2A202600794  
**Nhóm:** Dương Đức Cường (2A202600794), Đinh Hoàng Nam (2A202600884), Bùi Hoàng Sơn (2A202600925), Ngô Minh Khánh (2A202600953), Bùi Như Kiệt (2A202600895)  
**Ngày:** 03/06/2026

---

## 1. Track, product/app và user

**Track:** C — Food & Local Delivery  
**Product/app thật:** ShopeeFood  
**User cụ thể:** Người dùng trẻ (sinh viên, dân văn phòng) tại Hà Nội dùng các ứng dụng giao đồ ăn hàng ngày, thường xuyên băn khoăn "hôm nay ăn gì?", quan tâm đến budget, sức khỏe (lượng calo/dinh dưỡng) và bị ảnh hưởng bởi các yếu tố ngoại cảnh như thời tiết, thời gian trong ngày, tâm trạng.  
**Nhóm có phải user thật không?** Có. Cả 5 thành viên trong nhóm đều là sinh viên đại học thường xuyên gọi đồ ăn qua ShopeeFood. Cả nhóm đều trải qua pain point mất từ 10 - 15 phút lướt app vô định mỗi ngày chỉ vì ShopeeFood chỉ gợi ý các quán đang chạy quảng cáo hoặc quán nổi tiếng, bất kể thời tiết nắng/mưa hay thời gian sáng/đêm.

---

## 2. Evidence summary

| Evidence | Nguồn | User/pain nói lên điều gì? | SPEC phải đổi gì? |
|---|---|---|---|
| Mở ShopeeFood vào buổi sáng sớm nhưng được gợi ý lẩu thái, nướng buffet. Không có bộ lọc theo bữa ăn. | Self-use test #1 | App gợi ý sai ngữ cảnh thời gian, không phân biệt được các bữa ăn trong ngày. | Tích hợp thời gian thực của hệ thống để phân loại món ăn phù hợp (sáng: phở, bánh mì; đêm: đồ ăn vặt, quán mở khuya). |
| Trời mưa lạnh 18°C nhưng app liên tục đẩy banner gợi ý trà sữa đá và salad lạnh. | Self-use test #2 | App không nhận biết được thời tiết thực tế để điều chỉnh gợi ý phù hợp tâm sinh lý người dùng. | Tích hợp Weather API để detect thời tiết và đề xuất các món ấm/nóng khi trời mưa lạnh, món mát mẻ khi trời nắng nóng. |
| Tìm kiếm "quán ăn healthy gần đây dưới 50k" trả về kết quả lộn xộn, không lọc đúng. | Self-use test #3 | Search engine của app không hiểu ngôn ngữ tự nhiên chứa nhiều tiêu chí kết hợp (healthy + khoảng cách + budget). | Sử dụng LLM để phân tích prompt tự nhiên của user và mapping với dữ liệu từ Google Places API để lọc chính xác. |
| User muốn ăn kiêng nhưng món ăn không hề có thông tin calo hay dinh dưỡng. | Self-use test #4 | Thiếu thông tin hỗ trợ user có lối sống lành mạnh hoặc đang trong chế độ ăn kiêng. | Tích hợp cơ sở dữ liệu dinh dưỡng (Nutritionix API) để ước tính calo cho món ăn được gợi ý. |
| Khi buồn/stress muốn tìm comfort food ngọt hoặc cay nhưng app chỉ gợi ý quán trả tiền quảng cáo. | Self-use test #5 & #6 | App bỏ qua yếu tố tâm trạng - một động lực quan trọng của hành vi ăn uống. Gợi ý thiên vị quảng cáo làm giảm độ tin cậy. | Chatbot cho phép user chọn mood nhanh hoặc chia sẻ tâm trạng để gợi ý comfort food tương ứng, bỏ qua quán rác quảng cáo. |
| Đêm muộn (23h) app vẫn gợi ý quán đã đóng cửa từ 22h, đặt đơn bị hủy. | Self-use test #7 | Data giờ hoạt động của các quán ăn không được đồng bộ real-time với thuật toán gợi ý. | Sync real-time giờ mở cửa thông qua Google Places API trước khi đưa ra gợi ý cho user. |
| Tìm món dưới 50k, gợi ý cơm 45k ngon nhưng cách 5km phát sinh 25k ship → tổng đơn 70k vượt budget. | Self-use test #8 | Bỏ qua khoảng cách và phí ship khiến đề xuất vượt ngân sách thực tế của người dùng. | Tích hợp khoảng cách quán để ước tính phí ship thực tế và cộng vào budget tổng trước khi gợi ý. |
| Trải nghiệm đứt gãy khi phải copy và gõ tay tên quán từ chatbot sang ShopeeFood để đặt. | Self-use test #9 | Thiếu sự kết nối và liền mạch giữa gợi ý của chatbot và hành động đặt hàng thực tế. | Bổ sung nút Copy nhanh tên quán và deep-link dẫn đến trang tìm kiếm của ứng dụng giao đồ ăn. |
| Quán báo mở trên Google Maps nhưng thực tế trên ShopeeFood đang "Tạm ngưng nhận đơn" hoặc hết món. | Self-use test #10 | Trạng thái hoạt động và lượng tồn kho thực tế giữa các app giao đồ ăn bị lệch pha. | Gợi ý 1 món đi kèm danh sách 2-3 quán backup gần đó thay vì chỉ gợi ý duy nhất 1 quán để đề phòng. |

---

## 3. Pain statement

```text
Người dùng trẻ (sinh viên, dân văn phòng) hay phân vân "hôm nay ăn gì?" trên ShopeeFood
đang gặp khó khăn trong việc tìm món ăn phù hợp với ngữ cảnh thực tế và tối ưu chi phí,
vì hệ thống gợi ý của ShopeeFood chỉ tập trung vào các quán quảng cáo/phổ biến
mà hoàn toàn bỏ qua các yếu tố ngữ cảnh (thời tiết, thời điểm, tâm trạng, thông tin dinh dưỡng, phí ship phát sinh):
  - Gợi ý sai thời điểm (lẩu buổi sáng), sai thời tiết (kem lạnh ngày mưa bão), hoặc quán đã đóng cửa.
  - Gợi ý món trong budget nhưng quán ở quá xa khiến phí ship thực tế tăng cao làm tổng đơn vượt ngân sách.
  - Đứt gãy trải nghiệm khi user phải tự ghi nhớ và gõ lại tên quán từ chatbot sang ứng dụng đặt hàng.
  - Rủi ro quán gợi ý ngưng nhận đơn đột xuất trên app giao hàng.
Dẫn tới việc user mất 10-15 phút lướt app vô định, đặt đơn bị hủy hoặc vượt quá số tiền muốn chi, gây ức chế.
Bằng chứng: 10 phát hiện qua tự trải nghiệm thực tế (self-use) và phản hồi từ cộng đồng người dùng.
```

---

## 4. Build slice

```text
Dành cho người dùng trẻ hay phân vân "ăn gì" đang tìm kiếm món ăn trên ShopeeFood,
prototype sẽ là một AI Food Agent gợi ý món ăn thông minh theo ngữ cảnh:
  - Tự động detect thời tiết (Weather API) và thời gian thực để tạo ngữ cảnh nền (ví dụ: mưa lạnh buổi trưa).
  - Cho phép user trò chuyện tự nhiên hoặc click nhanh để chọn tâm trạng (mood: stress, vui vẻ, mệt mỏi)
    và yêu cầu cụ thể (budget dưới 50k, healthy/comfort food).
  - Truy vấn Google Places API để tìm các quán ăn thực tế gần vị trí của user đang mở cửa và có rating cao.
  - Tự động ước tính phí ship dựa trên khoảng cách địa lý (công thức: 15k cho 2km đầu + 5k/km tiếp theo)
    để đảm bảo tổng tiền (món + ship) nằm trong budget đã đặt ra của user.
  - Gợi ý 1 món ăn đi kèm danh sách 2-3 quán backup gần nhất cùng bán món đó (đề phòng quán chính ngưng nhận đơn).
  - Bổ sung nút "Copy tên quán nhanh" ngay trên giao diện chat giúp user dễ dàng dán vào ShopeeFood để đặt đơn.
  - Tích hợp Nutritionix API để bổ sung lượng calo ước tính cho món ăn gợi ý.
  - Output hiển thị 2-3 option tuyển chọn chi tiết kèm lý do gợi ý thuyết phục.
  - Xử lý failure mode: AI nhận dạng sai mood hoặc quán đóng cửa đột xuất bằng các nút bấm override/đổi món nhanh.
```

---

## 5. Auto/Aug decision

Chọn một:

- [x] **Augmentation:** AI gợi ý/draft/phân loại, user quyết cuối.
- [ ] **Conditional automation:** AI tự làm trong case hẹp; case mơ hồ/rủi ro chuyển người.
- [ ] **Automation:** AI tự quyết và tự hành động.

**Lý do chọn:** Lựa chọn ăn uống mang tính cá nhân, khẩu vị và cảm xúc rất chủ quan. AI đóng vai trò là một trợ lý thông minh (Co-pilot) giúp thu thập thông tin thời tiết, vị trí, giờ mở cửa và dinh dưỡng để "thu hẹp" lựa chọn từ hàng nghìn quán xuống còn 2-3 gợi ý phù hợp nhất. User luôn là người ra quyết định cuối cùng (Decider) xem có đặt món đó hay không và tự đặt trên app gốc.

**Human role:** Decider (Người quyết định) — User cung cấp thông tin tâm trạng, thay đổi các filter theo ý muốn, xem xét lý do gợi ý của AI và đưa ra quyết định đặt món hoặc yêu cầu đổi món khác.

---

## 6. Four paths

| Path | Prototype phải thể hiện gì? |
|---|---|
| **Happy** | Hệ thống tự detect trời mưa lạnh 20°C buổi trưa. User chat: *"Muốn ăn gì đó healthy ấm bụng dưới 60k"*. AI hiểu context, tìm qua API, ước lượng quán cách 1.2km có phí ship 15k, gợi ý: Phở gà ta xé (390 kcal, giá 40k + ship 15k = 55k, vừa khít budget) tại Quán Phở Việt + lý do: *"Húp nước dùng ấm nóng giải cảm, nhiều protein giúp tỉnh táo mà không béo"*. Kèm nút copy tên quán nhanh. User bấm copy. |
| **Low-confidence** | User nhập câu lệnh mơ hồ hoặc không rõ ràng: *"Ăn gì cũng được"*. AI không có đủ dữ liệu tâm trạng/budget → AI tự detect thời tiết + thời gian nền, đồng thời chủ động gợi ý nhanh bằng các nút bấm: *"Trưa hè nóng nực 35°C đấy! Bạn muốn một bữa 'Healthy lành mạnh' hay một bữa 'Nuông chiều bản thân' (comfort food) nào?"* để thu hẹp scope. |
| **Failure** | AI đoán sai mood/nhu cầu thực tế của user (Ví dụ: User đang buồn chán và thực tế muốn ăn đồ ngọt nhiều calo để giải sầu, nhưng AI vẫn gợi ý món cháo dinh dưỡng nhạt nhẽo vì thấy trời mưa lạnh). Hoặc gợi ý quán có phí ship thực tế bị tăng đột biến vượt xa budget ước tính ban đầu. |
| **Correction** | Khi gặp Failure Path (user phản đối gợi ý): User bấm nút *"Đổi món khác (muốn ăn ngọt/cay)"* hoặc chat *"Không muốn ăn healthy đâu"*. AI lập tức phản hồi: *"Xin lỗi bạn nhé, mình đổi vị ngay đây!"*, điều chỉnh bộ lọc sang comfort food, loại bỏ quán/món vừa gợi ý, và đưa ra 2 option mới (bánh ngọt/trà sữa nóng) phù hợp hơn. |

---

## 7. Failure mode nguy hiểm nhất

```text
Failure Mode 1: AI gợi ý sai lệch hoàn toàn so với tâm trạng hoặc nhu cầu dinh dưỡng thực tế của user.
Hậu quả: User thấy ức chế và chán nản, tắt chatbot ngay lập tức.
Cách xử lý:
  - Luôn đi kèm nút "Nuông chiều bản thân" (Comfort Mode) và "Giữ dáng" (Healthy Mode) nổi bật trên giao diện chat.
  - Cho user chọn các tag gợi ý nhanh: "Cay nồng", "Ngọt ngào", "Nhanh gọn", "Thanh đạm" để override nhanh.
  - AI lưu preference tạm thời trong session chat để không lặp lại gợi ý thuộc nhóm món ăn bị từ chối.

Failure Mode 2: Phí ship thực tế quá cao làm tổng chi phí vượt budget hoặc quán chính ngưng nhận đơn đột xuất trên ShopeeFood.
Hậu quả: User click vào đặt hàng nhưng phát hiện quá đắt hoặc không thể đặt được món, gây mất thời gian và giảm lòng tin vào AI.
Cách xử lý:
  - Hệ thống tự động tính khoảng cách địa lý và ước tính phí ship (15k cho 2km đầu, +5k mỗi km tiếp theo) để warning trước.
  - Phổ quát hóa thuật toán: Luôn đính kèm ít nhất 1-2 quán backup gần đó bán cùng món ăn để user chuyển hướng khi quán chính đóng cửa đột xuất.
  - Cung cấp nút copy nhanh tên quán giúp việc dán sang ShopeeFood kiểm tra trạng thái thực tế chỉ mất 2 giây.

Owner kiểm thử các path này là Bùi Hoàng Sơn (Tester).
```

---

## 8. Owner plan cho sáng Day 06

| Thành viên | Việc phụ trách | Bằng chứng cần có trong repo |
|---|---|---|
| **Dương Đức Cường** (Leader) | Phân tích & SPEC | Hoàn thiện [evidence-pack.md](evidence-pack.md), [synthesis-decide.md](synthesis-decide.md), và [thin-spec-day5.md](thin-spec-day5.md) |
| **Đinh Hoàng Nam** (Dev) | Prototype Development | Source code của chatbot UI (HTML/CSS/JS) chạy thử nghiệm local, có tích hợp gọi mock/real APIs (Weather, Google Maps, Nutritionix). |
| **Bùi Hoàng Sơn** (Tester) | Testing & Quality Assurance | File test_cases.md ghi nhận kết quả test 4 paths (Happy, Low-confidence, Failure, Correction) kèm ảnh chụp màn hình chạy test thực tế. |
| **Ngô Minh Khánh** (Business/UX) | User Feedback & Research | Bản khảo sát nhanh ý kiến user về ý tưởng gợi ý món theo ngữ cảnh + slide pitch giải pháp so với ShopeeFood gốc. |
| **Bùi Như Kiệt** (Writer/Support) | Demo Script & Repo Management | File demo_script.md định hướng video demo 3-5 phút (kịch bản thể hiện pain point của ShopeeFood gốc -> chạy demo prototype giải quyết 4 paths). |
