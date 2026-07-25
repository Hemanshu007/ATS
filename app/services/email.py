from app.tasks.email_tasks import send_status_change_email_task


def send_status_change_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    company_name: str,
    new_status: str,
):
    send_status_change_email_task.delay(
        candidate_email=candidate_email,
        candidate_name=candidate_name,
        job_title=job_title,
        company_name=company_name,
        new_status=new_status,
    )
