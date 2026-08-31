import os

# DEV ONLY: allows OAuth2 token exchange over http://localhost.
# Never do this in production — production must use https.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Prevents a crash if Google returns a slightly different scope set than
# requested (e.g. a scope wasn't actually granted) — we check for the
# missing scope ourselves below instead of letting oauthlib raise.
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.routes import router as auth_router
from app.routes.send import router as send_router
from app.routes.applicants import router as applicants_router
from app.routes.send_batch import router as send_batch_router
from app.routes.company import router as company_router
from app.db import Base, engine
from app.models import company, applicant  # noqa: F401 — needed so tables are registered

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HireMailer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # React dev server
        "https://hiremailer-frontend.vercel.app",  # deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(send_router)
app.include_router(applicants_router)
app.include_router(send_batch_router)
app.include_router(company_router)


@app.get("/")
def root():
    return {"status": "HireMailer backend running"}