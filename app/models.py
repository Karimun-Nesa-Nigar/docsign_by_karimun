from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    COMPLETED = "COMPLETED"

class FieldType(str, enum.Enum):
    SIGNATURE = "SIGNATURE"
    DATE = "DATE"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    status = Column(String, default=DocumentStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="documents")
    signers = relationship("Signer", back_populates="document")
    fields = relationship("Field", back_populates="document")
    audit_logs = relationship("AuditLog", back_populates="document")

class Signer(Base):
    __tablename__ = "signers"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    email = Column(String)
    name = Column(String)
    token = Column(String, unique=True, index=True)
    has_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="signers")
    fields = relationship("Field", back_populates="signer")

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    signer_id = Column(Integer, ForeignKey("signers.id"))
    page_number = Column(Integer)
    x_coordinate = Column(Integer)
    y_coordinate = Column(Integer)
    type = Column(String, default=FieldType.SIGNATURE)
    include_name = Column(Boolean, default=True)
    include_date = Column(Boolean, default=True)

    document = relationship("Document", back_populates="fields")
    signer = relationship("Signer", back_populates="fields")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    action = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String)
    user_agent = Column(String)

    document = relationship("Document", back_populates="audit_logs")
