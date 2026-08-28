from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db import Base
from app.services.crypto import EncryptedString


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    company_name = Column(String, nullable=True)
    refresh_token = Column(EncryptedString, nullable=False)
    access_token = Column(EncryptedString, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    connected_at = Column(DateTime(timezone=True), server_default=func.now())