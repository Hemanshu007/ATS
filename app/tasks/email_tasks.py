from contextlib import suppress

import structlog

from app.core.celery_app import celery_app
from app.core.config import settings

log = structlog.get_logger("ats.email")


def _mask_email(email: str) -> str:
    local, domain = email.split("@")
    return f"{local[:2]}***@{domain}"


def _send_via_ses(candidate_email: str, subject: str, body: str):
    with suppress(ImportError):
        import boto3
        client = boto3.client("ses", region_name=settings.AWS_REGION)
        client.send_email(
            Source=settings.MAIL_FROM,
            Destination={"ToAddresses": [candidate_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        log.info("email.sent_via_ses", to=_mask_email(candidate_email))


def _send_via_smtp(candidate_email: str, subject: str, body: str):
    import smtplib
    import ssl
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = candidate_email

    ctx = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls(context=ctx)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
    log.info("email.sent_via_smtp", to=_mask_email(candidate_email))


@celery_app.task(
    name="app.tasks.email_tasks.send_status_change_email_task",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
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

    transport = settings.EMAIL_TRANSPORT

    if not transport or transport == "log":
        log.info("email.skipped", to=_mask_email(candidate_email), subject=subject, transport=transport)
        return

    if transport == "ses":
        _send_via_ses(candidate_email, subject, body)
    elif transport == "smtp":
        if not settings.SMTP_USER:
            log.info("email.skipped_no_smtp", to=_mask_email(candidate_email), subject=subject)
            return
        _send_via_smtp(candidate_email, subject, body)
    else:
        log.warn("email.unknown_transport", transport=transport)
