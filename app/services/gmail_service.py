import requests
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, N8N_WEBHOOK_URL
from app.models.company import Company

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_valid_credentials(company: Company, db: Session) -> Credentials:
    creds = Credentials(
        token=company.access_token,
        refresh_token=company.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
        expiry=company.token_expiry,
    )

    if creds.expired or not creds.token:
        creds.refresh(GoogleRequest())
        company.access_token = creds.token
        company.token_expiry = creds.expiry
        db.commit()

    return creds


def send_email(company: Company, db: Session, to_email: str, subject: str, body: str) -> dict:
    # Token refresh still happens here, locally — unaffected by the block.
    creds = get_valid_credentials(company, db)

    payload = {
        "access_token": creds.token,
        "to_email": to_email,
        "subject": subject,
        "body": body,
    }

    response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()