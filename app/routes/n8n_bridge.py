from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.models.applicant import Applicant
from app.models.batch import Batch
from app.models.company import Company
from app.services.gmail_service import get_valid_credentials
from app.services.template import render_template
from app.config import N8N_SHARED_SECRET

router = APIRouter(prefix="/n8n", tags=["n8n"])


def _verify_secret(x_n8n_secret: Optional[str] = Header(None)):
    if not N8N_SHARED_SECRET or x_n8n_secret != N8N_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing secret")


@router.get("/pending-emails")
def get_pending_emails(
    limit: int = 5,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_secret),
):
    applicants = (
        db.query(Applicant)
        .filter(Applicant.status == "pending")
        .order_by(Applicant.id.asc())
        .limit(limit)
        .all()
    )

    results = []
    for applicant in applicants:
        batch = db.query(Batch).filter(Batch.id == applicant.batch_id).first()
        company = db.query(Company).filter(Company.id == applicant.company_id).first()
        if not batch or not company:
            continue

        try:
            creds = get_valid_credentials(company, db)
        except Exception as e:
            applicant.status = "failed"
            applicant.error_message = f"Token refresh failed: {e}"
            db.commit()
            continue

        subject = render_template(batch.subject_template, applicant.name, applicant.role)
        body = render_template(batch.body_template, applicant.name, applicant.role)

        results.append({
            "applicant_id": applicant.id,
            "access_token": creds.token,
            "to_email": applicant.email,
            "subject": subject,
            "body": body,
        })

    return {"emails": results}


class MarkResultPayload(BaseModel):
    applicant_id: int
    status: str  # "sent" or "failed"
    error_message: Optional[str] = None


@router.post("/mark-result")
def mark_result(
    payload: MarkResultPayload,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_secret),
):
    applicant = db.query(Applicant).filter(Applicant.id == payload.applicant_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")

    applicant.status = payload.status
    applicant.error_message = payload.error_message
    db.commit()

    return {"updated": True}