from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.company import Company
from app.auth.session import get_current_company

router = APIRouter(prefix="/company", tags=["company"])


@router.get("/me")
def get_my_company(company: Company = Depends(get_current_company)):
    """
    Returns the logged-in company's own info — used by the frontend on load
    to check if a company_name still needs to be collected.
    """
    return {
        "email": company.email,
        "company_name": company.company_name,
    }


class SetNameRequest(BaseModel):
    company_name: str


@router.post("/name")
def set_company_name(
    payload: SetNameRequest,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    name = payload.company_name.strip()
    if not name:
        return {"error": "Company name cannot be empty"}

    company.company_name = name
    db.commit()

    return {"company_name": company.company_name}