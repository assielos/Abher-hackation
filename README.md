# Absher Digital Evidence - CCTV Footage Request System

A digital solution for Absher services enabling users to request accident CCTV footage without physical visits.

## Features

- **Digital Request Submission**: Users submit requests with accident report, date, time, and national address
- **AI-Powered Report Verification**: OCR extracts data from Najm/Traffic reports and validates:
  - Report source authenticity
  - Date matching (within 1 day tolerance)
  - Time matching (within 2 hours tolerance)
  - Location verification using LocationIQ geocoding (within 5km radius)
- **Secure Token-Based Access**: Unique tokens for admin upload and user download
- **Request Tracking**: Real-time status updates with interactive map
- **Auto-Approval Demo**: Streamlined flow for demonstration

## Tech Stack

- **Backend**: Python, FastAPI, SQLite
- **Frontend**: HTML, CSS, JavaScript
- **APIs**: LocationIQ (geocoding)
- **OCR**: PyMuPDF for PDF text extraction

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npx serve -l 3000
# or
python -m http.server 3000
```

Then open: **http://localhost:3000/userr.html**

## Project Structure

```
backend/
  app/
    main.py           # FastAPI endpoints
    models.py         # Database models (SQLite)
    storage.py        # File storage handling
    report_verifier.py # AI OCR verification with LocationIQ
  data/               # SQLite DB + uploaded files

frontend/
  userr.html          # Main user page (submit request)
  admin.html          # Admin page (upload video)
  track.html          # Request tracking with map
  style.css           # Absher-themed styling
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/requests` | Submit new request |
| GET | `/api/requests/{id}` | Get request status |
| GET | `/api/requests/{id}/info` | Get request details (public) |
| POST | `/api/mock/moi/approve/{id}` | Mock MOI approval |
| GET | `/api/admin/requests/{id}/meta` | Get request meta (admin) |
| POST | `/api/admin/upload` | Upload video (admin) |
| GET | `/api/requests/{id}/download` | Download video |

## Workflow

```
User                    System                  Admin
  |                        |                      |
  |-- Submit Request ----->|                      |
  |                        |-- Verify Report      |
  |                        |-- Auto-Approve       |
  |                        |-- Generate Link ---->|
  |                        |                      |
  |                        |<---- Upload Video ---|
  |<-- Download Ready -----|                      |
  |                        |                      |
```

## Location Verification

Uses [LocationIQ API](https://locationiq.com/) to:
1. Geocode user's national address to coordinates
2. Compare with report coordinates (from Najm/Traffic PDF)
3. Calculate distance using Haversine formula
4. Verify location is within 5km radius

## Environment Variables (Optional)

```bash
FRONTEND_BASE_URL=http://localhost:3000
BACKEND_BASE_URL=http://localhost:8000
```

## License

MIT
