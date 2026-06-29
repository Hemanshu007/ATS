import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("ats.email")


def _mask_email(email: str) -> str:
    local, domain = email.split("@")
    return f"{local[:2]}***@{domain}"


def _send_smtp(msg: MIMEText, to: str):
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
    logger.info(f"Email sent to {_mask_email(to)}")


def send_status_change_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    company_name: str,
    new_status: str,
):
    subject = f"Application Update — {job_title} at {company_name}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Your application for {job_title} at {company_name} "
        f"has been updated to: {new_status.upper()}.\n\n"
        f"Best,\nATS Team"
    )

    if not settings.SMTP_USER:
        logger.info(f"[NO SMTP] To: {_mask_email(candidate_email)} | Subject: {subject}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = candidate_email

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _send_smtp, msg, candidate_email)
    except Exception as e:
        logger.error(f"Failed to send email to {candidate_email}: {e}")
