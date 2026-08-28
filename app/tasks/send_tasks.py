from app.celery_app import celery_app
from app.db import SessionLocal
from app.models.company import Company
from app.models.applicant import Applicant
from app.services.gmail_service import send_email
from app.services.template import render_template


@celery_app.task(name="send_single_applicant_email")
def send_single_applicant_email(applicant_id: int, subject_template: str, body_template: str):
    """
    Sends one email for one applicant, and updates their status in the DB.
    Runs in the Celery worker process, not in the main FastAPI request.
    """
    db = SessionLocal()
    try:
        applicant = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not applicant:
            return {"error": "applicant not found"}

        # Re-check status right before sending — if the batch was cancelled
        # after this task was already queued, skip it instead of sending.
        if applicant.status != "pending":
            return {"applicant_id": applicant_id, "status": applicant.status, "skipped": True}

        company = db.query(Company).filter(Company.id == applicant.company_id).first()
        if not company:
            applicant.status = "failed"
            applicant.error_message = "company not found"
            db.commit()
            return {"error": "company not found"}

        try:
            subject = render_template(subject_template, applicant.name, applicant.role)
            body = render_template(body_template, applicant.name, applicant.role)

            send_email(
                company=company,
                db=db,
                to_email=applicant.email,
                subject=subject,
                body=body,
            )

            applicant.status = "sent"
            applicant.error_message = None
        except Exception as e:
            applicant.status = "failed"
            applicant.error_message = str(e)

        db.commit()
        return {"applicant_id": applicant_id, "status": applicant.status}
    finally:
        db.close()


@celery_app.task(name="send_batch_emails")
def send_batch_emails(batch_id: str, subject_template: str, body_template: str, delay_seconds: int = 3):
    """
    Queues one send task per applicant in a batch, spaced apart by delay_seconds
    so we don't blast Gmail's API and trigger spam/rate-limit protections.
    """
    db = SessionLocal()
    try:
        applicants = db.query(Applicant).filter(
            Applicant.batch_id == batch_id,
            Applicant.status == "pending",
        ).all()

        for index, applicant in enumerate(applicants):
            send_single_applicant_email.apply_async(
                args=[applicant.id, subject_template, body_template],
                countdown=index * delay_seconds,  # stagger sends over time
            )

        return {"batch_id": batch_id, "queued": len(applicants)}
    finally:
        db.close()