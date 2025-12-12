# Absher CCTV Request Demo

Simple Python + JS demo for requesting accident CCTV footage with a mocked MOI approval flow, admin upload, and user download link.

## Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Optional environment variables:
```
set FRONTEND_BASE_URL=https://absher.gov.sa
set BACKEND_BASE_URL=https://api.absher.gov.sa
```

Key endpoints:
- `POST /api/requests` (multipart form: `national_address`, `street_name?`, `incident_date`, `incident_start`, `incident_end`, `report`)
- `GET /api/requests/{id}`
- `POST /api/mock/moi/approve/{id}` (simulate MOI approval)
- `GET /api/admin/requests/{id}/meta?token=...` (admin sees time/date/address)
- `POST /api/admin/upload?token=...&request_id=...` (multipart `video`)
- `GET /api/requests/{id}/download?token=...`

Data is stored in `backend/data/` (SQLite + uploaded files).

## Frontend

Open the static pages from `frontend/` (for local demo you can use a simple server):
```bash
cd frontend
python -m http.server 3000
```
- `userr.html`: الصفحة الرئيسية للمستفيد (طلب، متابعة، تحميل).
- `admin.html`: صفحة مسؤول التخزين (استعراض وقت/تاريخ اللقطة ورفع الفيديو).

Update `API_BASE` in the JS files if you change ports.

