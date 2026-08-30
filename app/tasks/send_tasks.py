import time
from app.db import SessionLocal
from app.models.company import Company
from app.models.applicant import Applicant
from app.services.gmail_service import send_email
from app.services.template import render_template


def send_single_applicant_email(applicant_id: int, subject_template: str, body_template: str):
    """
    Sends one email for one applicant, and updates their status in the DB.
    """
    db = SessionLocal()
    try:
        applicant = db.query(Applicant).filter(Applicant.id == applicant_id).first()
        if not applicant:
            return {"error": "applicant not found"}

        # Re-check status right before sending — if the batch was cancelled
        # after this was queued, skip it instead of sending.
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


def send_batch_emails(batch_id: str, subject_template: str, body_template: str, delay_seconds: int = 3):
    """
    Runs as a FastAPI BackgroundTask — works through every pending applicant
    in a batch, one at a time, waiting delay_seconds between each so we don't
    blast Gmail's API and trigger spam/rate-limit protections.

    This function itself is what gets handed to BackgroundTasks.add_task(),
    so it runs after the HTTP response has already been sent to the browser —
    the person doesn't wait for it to finish.
    """
    db = SessionLocal()
    try:
        applicants = db.query(Applicant).filter(
            Applicant.batch_id == batch_id,
            Applicant.status == "pending",
        ).all()
        applicant_ids = [a.id for a in applicants]
    finally:
        db.close()

    for index, applicant_id in enumerate(applicant_ids):
        if index > 0:
            time.sleep(delay_seconds)
        send_single_applicant_email(applicant_id, subject_template, body_template)

    return {"batch_id": batch_id, "processed": len(applicant_ids)}