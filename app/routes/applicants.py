import uuid
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.company import Company
from app.models.applicant import Applicant
from app.services.csv_parser import parse_applicants_file
from app.auth.session import get_current_company

router = APIRouter(prefix="/applicants", tags=["applicants"])


GMAIL_DAILY_SEND_LIMIT = 500  # regular Gmail account cap; Workspace is ~2000


@router.post("/upload")
async def upload_applicants(
    file: UploadFile = File(...),
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV or Excel file (columns: name, role, email) for the
    company identified by the caller's session token.
    Saves all rows to the database under a new batch_id, ready to be sent.
    """
    file_bytes = await file.read()
    try:
        applicants_data = parse_applicants_file(file.filename, file_bytes)
    except ValueError as e:
        return {"error": str(e)}

    if not applicants_data:
        return {"error": "The file has no applicant rows."}

    # Drop duplicate (email, role) pairs — keep the first occurrence only.
    # Same email with a DIFFERENT role is kept (someone applying for two roles
    # is legitimate); same email with the SAME role twice is a true duplicate.
    seen_pairs = set()
    deduplicated = []
    duplicate_count = 0
    for row in applicants_data:
        key = (row["email"].strip().lower(), row["role"].strip().lower())
        if key in seen_pairs:
            duplicate_count += 1
            continue
        seen_pairs.add(key)
        deduplicated.append(row)

    applicants_data = deduplicated

    batch_id = str(uuid.uuid4())

    for row in applicants_data:
        applicant = Applicant(
            company_id=company.id,
            batch_id=batch_id,
            name=row["name"],
            role=row["role"],
            email=row["email"],
        )
        db.add(applicant)

    db.commit()

    warnings = []
    if len(applicants_data) > GMAIL_DAILY_SEND_LIMIT:
        warnings.append(
            f"This batch has {len(applicants_data)} applicants, which exceeds Gmail's "
            f"~{GMAIL_DAILY_SEND_LIMIT}/day sending limit for a regular account. "
            f"Sends beyond the limit may be delayed or blocked by Gmail."
        )
    if duplicate_count:
        warnings.append(
            f"{duplicate_count} exact duplicate row(s) removed (same email and same role) — "
            f"only the first occurrence of each was kept."
        )

    return {
        "batch_id": batch_id,
        "count": len(applicants_data),
        "sample": applicants_data[0],  # used by the frontend to render a live preview
        "warnings": warnings,
        "message": "Applicants uploaded. Use this batch_id to trigger sending.",
    }