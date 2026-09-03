from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.applicant import Applicant
from app.models.company import Company
from app.models.batch import Batch
from app.auth.session import get_current_company

router = APIRouter(prefix="/send", tags=["send"])


class SendBatchRequest(BaseModel):
    batch_id: str
    subject_template: str
    body_template: str
    delay_seconds: int = 3  # kept for frontend compatibility; no longer used internally


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
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """
    Saves the batch's subject/body template so n8n can pick it up.
    No longer sends anything itself — n8n polls for pending applicants
    (via /n8n/pending-emails) and sends them via Gmail directly.
    """
    _verify_batch_ownership(payload.batch_id, company, db)

    existing = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if existing:
        existing.subject_template = payload.subject_template
        existing.body_template = payload.body_template
    else:
        db.add(Batch(
            id=payload.batch_id,
            company_id=company.id,
            subject_template=payload.subject_template,
            body_template=payload.body_template,
        ))
    db.commit()

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
    'cancelled' — n8n's polling query only picks up 'pending' applicants,
    so this will be skipped on the next poll.
    """
    _verify_batch_ownership(batch_id, company, db)

    updated = db.query(Applicant).filter(
        Applicant.batch_id == batch_id,
        Applicant.status == "pending",
    ).update({"status": "cancelled"})

    db.commit()

    return {"cancelled_count": updated}