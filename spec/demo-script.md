# Demo Script - 5 phút

## Chuẩn bị

- Chạy app tại `http://localhost:8000`.
- Cho phép quyền Location.
- Chuẩn bị một tab DevTools hoặc terminal chạy `python -m pytest -q`.
- Nếu API ngoài không ổn định, chuẩn bị screenshot/video backup nhưng vẫn demo ít nhất một lời gọi AI thật.

## 0:00-0:45 - Problem

ShopeeFood có nhiều quán nhưng người dùng vẫn mất thời gian vì gợi ý thường không hiểu "lúc này": thời tiết, bữa ăn, mood, budget thật gồm ship và vị trí hiện tại.

## 0:45-1:15 - Solution và quyết định AI

Yumi là AI copilot, không tự đặt hàng. Agent hiểu yêu cầu tự nhiên, tổng hợp context, chọn quán chính + backup và giải thích. User vẫn là người quyết định.

## 1:15-2:30 - Happy path

Nhập:

```text
Trời mưa, mình muốn ăn phở dưới 70k gần đây.
```

Chỉ ra:

- AI chạy thật để hiểu intent.
- GPS và Geoapify tìm quán gần.
- Card có khoảng cách, món, giá, phí ship, tổng chi phí và dinh dưỡng.
- Có lựa chọn backup.

Hỏi tiếp:

```text
Quán đầu tiên cách chỗ tôi bao xa và ở địa chỉ nào?
```

Chỉ ra Agent nhớ context nhiều lượt.

## 2:30-3:20 - Correction path

Nhập:

```text
Không muốn ăn món này, đổi món khác đi.
```

Chỉ ra Yumi ghi nhận lựa chọn bị từ chối và không lặp lại trong lần gợi ý mới.

## 3:20-4:05 - Error path

Từ chối/tắt quyền Location rồi reload app. Nhập:

```text
Quán nào gần tôi nhất?
```

Kỳ vọng: Yumi yêu cầu bật quyền vị trí, không dùng Gia Lâm hay tọa độ giả để trả khoảng cách.

## 4:05-4:35 - Trust và giới hạn

- Menu, giá, phí ship và dữ liệu thay thế được gắn nhãn ước tính.
- Geoapify không biết trạng thái nhận đơn của ShopeeFood.
- Yumi không tự checkout; user kiểm tra và đặt trên app gốc.

## 4:35-5:00 - Evidence và kết quả

- Build slice xuất phát từ 10 self-use observations và nguồn ngoài nhóm.
- Automated suite: 76 tests.
- Lessons learned: AI product không chỉ là prompt; cần guardrail, nguồn dữ liệu, correction và thiết kế khi thiếu context.
