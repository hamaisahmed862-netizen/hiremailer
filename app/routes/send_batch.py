from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tasks.send_tasks import send_batch_emails
from app.db import get_db
from app.models.applicant import Applicant
from app.models.company import Company
from app.auth.session import get_current_company

router = APIRouter(prefix="/send", tags=["send"])


class SendBatchRequest(BaseModel):
    batch_id: str
    subject_template: str
    body_template: str
    delay_seconds: int = 3  # gap between each send, in seconds


def _verify_batch_ownership(batch_id: str, company: Company, db: Session):
    """Raises 404 if this batch doesn't belong to the requesting company."""
    exists = db.query(Applicant).filter(
        Applicant.batch_id == batch_id,
        Applicant.company_id == company.id,
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Batch not found")


@router.post("/batch")
def trigger_batch_send(
    payload: SendBatchRequest,
    background_tasks: BackgroundTasks,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """
    Kicks off sending for an uploaded batch. Returns immediately — actual
    sending happens after the response, via FastAPI's BackgroundTasks.
    """
    _verify_batch_ownership(payload.batch_id, company, db)

    background_tasks.add_task(
        send_batch_emails,
        payload.batch_id,
        payload.subject_template,
        payload.body_template,
        payload.delay_seconds,
    )
    return {"queued": True}


@router.get("/batch/{batch_id}/status")
def batch_status(
    batch_id: str,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """
    Check progress of a batch — how many sent, failed, cancelled, or still pending.
    """
    _verify_batch_ownership(batch_id, company, db)

    applicants = db.query(Applicant).filter(Applicant.batch_id == batch_id).all()

    summary = {"total": len(applicants), "sent": 0, "failed": 0, "pending": 0, "cancelled": 0}
    details = []
    for a in applicants:
        summary[a.status] = summary.get(a.status, 0) + 1
        details.append({"name": a.name, "email": a.email, "status": a.status, "error": a.error_message})

    return {"summary": summary, "details": details}


@router.post("/batch/{batch_id}/cancel")
def cancel_batch(
    batch_id: str,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """
    Stops a batch mid-send. Any applicant still 'pending' is marked
    'cancelled' — the running background task checks this status right
    before each send and will skip instead of sending.
    """
    _verify_batch_ownership(batch_id, company, db)

    updated = db.query(Applicant).filter(
        Applicant.batch_id == batch_id,
        Applicant.status == "pending",
    ).update({"status": "cancelled"})

    db.commit()

    return {"cancelled_count": updated}