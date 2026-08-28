from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import requests

from app.auth.oauth import get_flow
from app.auth.session import create_session_token
from app.db import get_db
from app.models.company import Company

router = APIRouter(prefix="/auth", tags=["auth"])

# DEV ONLY: in-memory store mapping state -> code_verifier.
# This resets whenever the server restarts, and won't work across
# multiple server processes. We'll replace this with Redis/DB later.
_pkce_store = {}


@router.get("/google")
def login_with_google():
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",       # needed to get a refresh_token
        include_granted_scopes="true",
        prompt="consent",            # forces refresh_token on every connect
    )
    _pkce_store[state] = flow.code_verifier
    return RedirectResponse(auth_url)


@router.get("/callback")
def google_callback(request: Request, db: Session = Depends(get_db)):
    state = request.query_params.get("state")
    code_verifier = _pkce_store.pop(state, None)

    flow = get_flow()
    flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=str(request.url))

    credentials = flow.credentials

    # Google may grant fewer scopes than requested if the person didn't
    # check the "send email" permission box on the consent screen.
    # Catch that here instead of saving a connection that can't actually send.
    granted_scopes = set(credentials.scopes or [])
    if "https://www.googleapis.com/auth/gmail.send" not in granted_scopes:
        return RedirectResponse(
            "http://localhost:5173?connect_error="
            "Gmail send permission wasn't granted. Please reconnect and make "
            "sure to approve the 'send email on your behalf' permission."
        )

    # Ask Google who this is, so we know which company record to save.
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
    ).json()
    email = userinfo.get("email")

    # Upsert: update if this company already connected before, else create.
    existing = db.query(Company).filter(Company.email == email).first()
    if existing:
        existing.refresh_token = credentials.refresh_token or existing.refresh_token
        existing.access_token = credentials.token
        existing.token_expiry = credentials.expiry
    else:
        existing = Company(
            email=email,
            refresh_token=credentials.refresh_token,
            access_token=credentials.token,
            token_expiry=credentials.expiry,
        )
        db.add(existing)

    db.commit()

    # Issue a signed session token proving who this is — the frontend
    # will send this back on every future request instead of a plain email.
    token = create_session_token(existing.id)

    return RedirectResponse(
        f"http://localhost:5173?session_token={token}&connected_email={email}"
    )