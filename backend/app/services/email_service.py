"""
Email Service — gửi email qua SMTP với fail-soft policy.

Design notes:
- Async qua aiosmtplib (fit FastAPI event loop, không block).
- Demo mode: SMTP_USER rỗng → log content ra console với prefix [EMAIL DEV MODE],
  KHÔNG raise. Tester/dev chạy không cần SMTP server.
- Production: Gmail App Password (yêu cầu 2FA + App Password 16 ký tự, không phải password thường).
- Fail-soft: nếu SMTP fail (timeout, auth lỗi, server lỗi) → log warning + return False,
  KHÔNG raise. Caller (notification.py) tự quyết định có log email_sent_at không.
- Templates Jinja2 từ backend/app/templates/email/. Auto-escape HTML để tránh XSS
  từ student name / reason text.

Usage:
    ok = await email_service.send(
        to="sv@example.com",
        subject="[HCMUT] Cảnh báo học vụ mức 1",
        template_name="warning_level_1",
        context={"full_name": "Nguyễn Văn A", "gpa": 1.15, "semester": "242"},
    )
"""
from __future__ import annotations

import asyncio
import socket
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from app.core.config import settings


_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _is_demo_mode() -> bool:
    """Demo mode khi chưa cấu hình SMTP_USER hoặc EMAIL_ENABLED=False."""
    return not settings.EMAIL_ENABLED or not settings.SMTP_USER


def _render_template(template_name: str, context: dict[str, Any]) -> tuple[str, str]:
    """Render HTML + plaintext fallback. Trả (html_body, text_body)."""
    enriched_context = {
        **context,
        "app_base_url": settings.APP_BASE_URL,
        "from_name": settings.EMAIL_FROM_NAME,
    }
    html_template = _jinja_env.get_template(f"{template_name}.html")
    html_body = html_template.render(**enriched_context)

    text_template_path = _TEMPLATES_DIR / f"{template_name}.txt"
    if text_template_path.exists():
        text_template = _jinja_env.get_template(f"{template_name}.txt")
        text_body = text_template.render(**enriched_context)
    else:
        text_body = (
            f"{context.get('subject', 'Thông báo từ HCMUT')}\n\n"
            f"Vui lòng đăng nhập {settings.APP_BASE_URL} để xem chi tiết."
        )
    return html_body, text_body


def _build_message(
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


async def send(
    *,
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> bool:
    """
    Gửi email. Trả True nếu gửi thành công (hoặc demo mode log thành công),
    False nếu SMTP fail.

    Không bao giờ raise — fail-soft theo design M6.
    """
    if not to or "@" not in to:
        logger.warning(f"[email_service] Invalid recipient: {to!r}")
        return False

    try:
        html_body, text_body = _render_template(template_name, context)
    except Exception as exc:
        logger.error(f"[email_service] Template render failed: {template_name} — {exc}")
        return False

    if _is_demo_mode():
        logger.info(
            f"[EMAIL DEV MODE] To={to} | Subject={subject} | Template={template_name} "
            f"| Context keys={list(context.keys())}"
        )
        return True

    message = _build_message(to, subject, html_body, text_body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            timeout=20,
        )
        logger.info(f"[email_service] Sent to {to} | template={template_name}")
        return True
    except (aiosmtplib.SMTPException, OSError, socket.gaierror, asyncio.TimeoutError) as exc:
        logger.warning(
            f"[email_service] SMTP fail to={to} template={template_name} — {exc.__class__.__name__}: {exc}"
        )
        return False


def fire_and_forget(
    *,
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> asyncio.Task:
    """
    Spawn task gửi email không await — caller (API endpoint) không bị block bởi SMTP.
    Trả task để test/cleanup nếu cần.
    """
    return asyncio.create_task(
        send(to=to, subject=subject, template_name=template_name, context=context)
    )
