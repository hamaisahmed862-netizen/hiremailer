import base64
from email.mime.text import MIMEText

import httplib2
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from app.models.company import Company

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_valid_credentials(company: Company, db: Session) -> Credentials:
    """
    Builds a Credentials object from the company's saved tokens.
    If the access token has expired, refreshes it using the refresh_token
    and saves the new access token back to the database.
    """
    creds = Credentials(
        token=company.access_token,
        refresh_token=company.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )

    if creds.expired or not creds.token:
        creds.refresh(GoogleRequest())
        # Save the refreshed access token so we don't refresh again unnecessarily
        company.access_token = creds.token
        company.token_expiry = creds.expiry
        db.commit()

    return creds


def send_email(company: Company, db: Session, to_email: str, subject: str, body: str) -> dict:
    """
    Sends a single email via Gmail API, using the company's connected account.
    Returns Gmail's API response (contains the sent message id).
    """
    creds = get_valid_credentials(company, db)

    # googleapiclient uses httplib2 internally, which — unlike the
    # `requests` library — doesn't automatically read http_proxy/https_proxy
    # from the environment. Some hosts (like PythonAnywhere's free tier)
    # require outbound traffic to go through a proxy, so we wire it in
    # explicitly here using httplib2's own env-reading helper.
    proxy_info = httplib2.proxy_info_from_environment(method="https")
    http = httplib2.Http(proxy_info=proxy_info)
    authed_http = AuthorizedHttp(creds, http=http)

    # static_discovery=True avoids an extra network call to fetch API
    # metadata from www.googleapis.com at runtime — uses the discovery
    # document bundled with the library instead.
    service = build("gmail", "v1", http=authed_http, static_discovery=True)

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    sent = service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()

    return sent