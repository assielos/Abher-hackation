from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from . import models, storage, report_verifier

# Force unbuffered output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("app")

app = FastAPI(title="Absher CCTV Request Demo")

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


# Middleware to log every request and catch errors
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"[MIDDLEWARE] Incoming: {request.method} {request.url}", flush=True)
        logger.info("Incoming request: %s %s", request.method, request.url)
        try:
            response = await call_next(request)
            print(f"[MIDDLEWARE] Response status: {response.status_code}", flush=True)
            return response
        except Exception as exc:
            print(f"[MIDDLEWARE] Exception: {exc}", flush=True)
            traceback.print_exc()
            return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.init_db()


# Simple test endpoint
@app.get("/api/ping")
async def ping():
    print("[PING] Received ping request", flush=True)
    return {"message": "pong"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ANN001
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


class VerificationInfo(BaseModel):
    confidence: int
    message: str
    is_valid_source: bool
    source_name: str
    date_match: bool
    time_match: bool
    location_match: bool
    matches: dict


class SubmitResponse(BaseModel):
    request_id: int
    upload_token: str
    admin_link: str
    status: str = "PENDING_APPROVAL"
    verification: Optional[VerificationInfo] = None


class StatusResponse(BaseModel):
    request_id: int
    status: str
    download_token: Optional[str] = None
    download_expires_at: Optional[str] = None


@app.post(
    "/api/requests",
    response_model=SubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    national_address: str = Form(...),
    incident_date: str = Form(...),
    incident_start: str = Form(...),
    incident_end: str = Form(...),
    street_name: str | None = Form(None),
    report: UploadFile = File(...),
):
    print(f"[CREATE_REQUEST] Function called!", flush=True)
    print(f"[CREATE_REQUEST] national_address={national_address}", flush=True)
    print(f"[CREATE_REQUEST] incident_date={incident_date}", flush=True)
    print(f"[CREATE_REQUEST] report={report.filename}", flush=True)
    logger.info("create_request called with address=%s", national_address)
    try:
        content = await report.read()
        request_id = models.create_request(
            "user",  # Default user ID (SMS removed)
            national_address,
            incident_date,
            incident_start,
            incident_end,
            Path(report.filename),
            street_name=street_name,
        )
        saved_path = storage.save_report_file(request_id, report.filename, content)
        logger.info("Saved report to %s", saved_path)
        models.update_report_path(request_id, saved_path)
        
        # Verify report using OCR
        verification = None
        try:
            verify_result = report_verifier.verify_report(
                pdf_path=saved_path,
                user_date=incident_date,
                user_start_time=incident_start,
                user_end_time=incident_end,
                user_address=national_address,
            )
            verification = VerificationInfo(
                confidence=verify_result.confidence,
                message=verify_result.message,
                is_valid_source=verify_result.is_valid_source,
                source_name=verify_result.source_name,
                date_match=verify_result.date_match,
                time_match=verify_result.time_match,
                location_match=verify_result.location_match,
                matches=verify_result.matches,
            )
            logger.info("Verification result: confidence=%d", verify_result.confidence)
            
            # Decision based on confidence level
            if verify_result.confidence < 80:
                # Reject if confidence < 80%
                models.reject_request(request_id)
                request_status = models.STATUS_REJECTED
                logger.info("Request %d rejected due to low confidence (%d%%)", request_id, verify_result.confidence)
            elif verify_result.confidence >= 95:
                # Auto-approve if confidence >= 95%
                models.approve_request(request_id)
                request_status = models.STATUS_APPROVED
                logger.info("Request %d auto-approved with high confidence (%d%%)", request_id, verify_result.confidence)
            else:
                # Pending review if confidence 80-94%
                request_status = models.STATUS_PENDING
                logger.info("Request %d pending review with confidence (%d%%)", request_id, verify_result.confidence)
                
        except Exception as ve:
            logger.warning("Verification failed: %s", ve)
            request_status = models.STATUS_PENDING
        
        upload_token = models.get_upload_token(request_id)
        admin_link = f"{FRONTEND_BASE_URL}/admin.html?request_id={request_id}&token={upload_token}"
        return SubmitResponse(
            request_id=request_id,
            upload_token=upload_token,
            admin_link=admin_link,
            status=request_status,
            verification=verification,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Create request failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/requests/{request_id}", response_model=StatusResponse)
async def get_status(request_id: int):
    req = models.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    return StatusResponse(
        request_id=req["id"],
        status=req["status"],
        download_token=req["download_token"],
        download_expires_at=req["download_expires_at"],
    )


@app.post("/api/mock/moi/approve/{request_id}")
async def mock_approve(request_id: int):
    req = models.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    if req["status"] not in (models.STATUS_PENDING, models.STATUS_REJECTED):
        return {"message": f"Already {req['status']}"}
    models.approve_request(request_id)
    return {"message": "Approved"}


class AdminMetaResponse(BaseModel):
    request_id: int
    national_address: str
    street_name: str | None
    incident_date: str
    incident_start: str
    incident_end: str
    status: str


class PublicRequestInfo(BaseModel):
    request_id: int
    national_address: str
    incident_date: str
    incident_start: str
    incident_end: str
    status: str


@app.get("/api/requests/{request_id}/info", response_model=PublicRequestInfo)
async def get_request_info(request_id: int):
    """Public endpoint for tracking - no token required."""
    req = models.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    return PublicRequestInfo(
        request_id=req["id"],
        national_address=req["national_address"],
        incident_date=req["incident_date"],
        incident_start=req["incident_start"],
        incident_end=req["incident_end"],
        status=req["status"],
    )


@app.get("/api/admin/requests/{request_id}/meta", response_model=AdminMetaResponse)
async def admin_meta(request_id: int, token: str):
    expected = models.get_upload_token(request_id)
    if not expected or token != expected:
        raise HTTPException(status_code=403, detail="Invalid upload token.")
    req = models.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    return AdminMetaResponse(
        request_id=req["id"],
        national_address=req["national_address"],
        street_name=req["street_name"],
        incident_date=req["incident_date"],
        incident_start=req["incident_start"],
        incident_end=req["incident_end"],
        status=req["status"],
    )


class UploadResponse(BaseModel):
    message: str
    download_token: str
    download_expires_at: str


@app.post("/api/admin/upload", response_model=UploadResponse)
async def upload_video(token: str, request_id: int, video: UploadFile = File(...)):
    expected_token = models.get_upload_token(request_id)
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid upload token.")
    req = models.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    if req["status"] != models.STATUS_APPROVED:
        raise HTTPException(status_code=400, detail="Request not approved yet.")

    content = await video.read()
    saved = storage.save_video_file(request_id, video.filename, content)
    logger.info("Saved video to %s", saved)
    download_token = models.make_download_ready(request_id)
    req = models.get_request(request_id)
    return UploadResponse(
        message="Upload received",
        download_token=download_token,
        download_expires_at=req["download_expires_at"],
    )


@app.get("/api/requests/{request_id}/download")
async def download_video(request_id: int, token: str):
    valid, reason = models.validate_download_token(request_id, token)
    if not valid:
        raise HTTPException(status_code=403, detail=reason)
    file_path, found = storage.get_video_file(request_id)
    if not found:
        raise HTTPException(status_code=404, detail="Video not found.")
    return FileResponse(path=file_path, filename=file_path.name, media_type="video/mp4")

