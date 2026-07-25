import smtplib
from email.mime.text import MIMEText

import structlog
from app.core.celery_app import celery_app
from app.core.config import settings

log = structlog.get_logger("ats.email")


def _mask_email(email: str) -> str:
    local, domain = email.split("@")
    return f"{local[:2]}***@{domain}"


@celery_app.task(
    name="app.tasks.email_tasks.send_status_change_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_status_change_email_task(
    self,
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
        log.info("email.skipped_no_smtp", to=_mask_email(candidate_email), subject=subject)
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = candidate_email

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        log.info("email.sent", to=_mask_email(candidate_email), status=new_status)
    except Exception as exc:
        log.error("email.failed", to=_mask_email(candidate_email), error=str(exc))
        raise self.retry(exc=exc)
