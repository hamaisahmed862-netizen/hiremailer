from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db import Base


class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    batch_id = Column(String, nullable=False, index=True)  # groups one CSV upload together

    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, nullable=False)

    status = Column(String, default="pending")  # pending, sent, failed
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())