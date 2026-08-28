from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import SESSION_SECRET_KEY
from app.db import get_db
from app.models.company import Company

SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days

_serializer = URLSafeTimedSerializer(SESSION_SECRET_KEY, salt="hiremailer-session")


def create_session_token(company_id: int) -> str:
    return _serializer.dumps({"company_id": company_id})


def verify_session_token(token: str) -> int:
    """Returns company_id if valid, raises ValueError if not."""
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
        return data["company_id"]
    except SignatureExpired:
        raise ValueError("Session expired, please reconnect Gmail")
    except BadSignature:
        raise ValueError("Invalid session token")


def get_current_company(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Company:
    """
    FastAPI dependency: reads the Bearer token from the Authorization header,
    verifies it, and returns the matching Company — or raises 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        company_id = verify_session_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=401, detail="Company not found")

    return company