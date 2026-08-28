from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.company import Company
from app.services.gmail_service import send_email
from app.services.template import render_template

router = APIRouter(prefix="/send", tags=["send"])


@router.get("/test")
def send_test_email(
    company_email: str,
    to_email: str,
    name: str,
    role: str,
    db: Session = Depends(get_db),
):
    """
    Quick manual test:
    /send/test?company_email=your-connected-gmail@gmail.com&to_email=someone@example.com&name=Ali&role=Backend Developer
    """
    company = db.query(Company).filter(Company.email == company_email).first()
    if not company:
        return {"error": "No connected company found with that email"}

    template = "Hi {{name}}, thanks for applying for the {{role}} role. We'll be in touch soon!"
    body = render_template(template, name, role)

    result = send_email(
        company=company,
        db=db,
        to_email=to_email,
        subject=f"Your application for {role}",
        body=body,
    )

    return {"sent": True, "gmail_message_id": result.get("id")}