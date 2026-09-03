from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True)  # same value as Applicant.batch_id
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    subject_template = Column(String, nullable=False)
    body_template = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())