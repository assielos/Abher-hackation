"""
Email notification module using SMTP.
Set environment variables:
- EMAIL_SMTP_HOST (default: smtp.gmail.com)
- EMAIL_SMTP_PORT (default: 587)
- EMAIL_SENDER (your email)
- EMAIL_PASSWORD (app password for Gmail)
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("email")

SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_email(to_email: str, subject: str, body_html: str) -> bool:
    """
    Send email notification. Returns True if sent, False otherwise.
    If credentials not configured, logs the email for demo purposes.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        logger.info("Email (demo) to %s: %s - %s", to_email, subject, body_html[:100])
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email

        # Plain text version
        text_body = body_html.replace("<br>", "\n").replace("</p>", "\n")
        import re
        text_body = re.sub(r"<[^>]+>", "", text_body)

        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(body_html, "html", "utf-8")

        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())

        logger.info("Email sent successfully to %s", to_email)
        return True

    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False


def send_admin_notification(request_id: int, admin_link: str, incident_date: str, incident_time: str) -> bool:
    """Send notification to admin about new request."""
    subject = f"طلب جديد #{request_id} - لقطات كاميرات"
    body = f"""
    <div dir="rtl" style="font-family: Tajawal, Arial, sans-serif; padding: 20px;">
        <h2 style="color: #0c8a3e;">طلب جديد #{request_id}</h2>
        <p>تم استلام طلب جديد للقطات الكاميرات.</p>
        <p><strong>التاريخ:</strong> {incident_date}</p>
        <p><strong>الوقت:</strong> {incident_time}</p>
        <p style="margin-top: 20px;">
            <a href="{admin_link}" style="background: #0c8a3e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px;">
                رفع الفيديو
            </a>
        </p>
    </div>
    """
    admin_email = os.getenv("ADMIN_EMAIL", "")
    if admin_email:
        return send_email(admin_email, subject, body)
    logger.info("Admin email not configured, skipping email notification")
    return False


def send_user_notification(user_email: str, request_id: int, download_url: str, incident_info: dict) -> bool:
    """Send notification to user when video is ready."""
    subject = f"فيديو الحادث جاهز - طلب #{request_id}"
    body = f"""
    <div dir="rtl" style="font-family: Tajawal, Arial, sans-serif; padding: 20px;">
        <h2 style="color: #0c8a3e;">تم تجهيز الفيديو</h2>
        <p>فيديو الحادث للطلب رقم <strong>#{request_id}</strong> جاهز للتحميل.</p>
        <p><strong>العنوان:</strong> {incident_info.get('address', '-')}</p>
        <p><strong>التاريخ:</strong> {incident_info.get('date', '-')}</p>
        <p><strong>الوقت:</strong> من {incident_info.get('start', '-')} إلى {incident_info.get('end', '-')}</p>
        <p style="margin-top: 20px;">
            <a href="{download_url}" style="background: #0c8a3e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px;">
                تحميل الفيديو
            </a>
        </p>
        <p style="margin-top: 20px; color: #666; font-size: 13px;">
            هذا الرابط صالح لمدة 24 ساعة.
        </p>
    </div>
    """
    if user_email:
        return send_email(user_email, subject, body)
    return False

