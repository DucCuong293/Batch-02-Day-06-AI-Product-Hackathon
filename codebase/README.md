# Codebase

Prototype nằm trong [`ai-food-agent/`](ai-food-agent/).

## Chạy nhanh

```powershell
cd ai-food-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item .env.example .env
cd backend
python main.py
```

Mở `http://localhost:8000` và cấp quyền vị trí cho trình duyệt.

## Kiểm thử

```powershell
cd ai-food-agent
pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Không commit `.env`. Danh sách biến môi trường được mô tả trong `ai-food-agent/.env.example`.
