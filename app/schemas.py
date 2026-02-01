from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .models import DocumentStatus, FieldType

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class SignerCreate(BaseModel):
    email: str
    name: str

class Signer(SignerCreate):
    id: int
    document_id: int
    has_signed: bool
    signed_at: Optional[datetime] = None
    class Config:
        orm_mode = True

class FieldCreate(BaseModel):
    signer_email: str # Use email to lookup signer in the context of the doc
    page_number: int
    x_coordinate: int
    y_coordinate: int
    type: FieldType = FieldType.SIGNATURE
    include_name: bool = True
    include_date: bool = True

class Field(BaseModel):
    id: int
    signer_id: int
    page_number: int
    x_coordinate: int
    y_coordinate: int
    type: str # Enum as string
    include_name: bool = True
    include_date: bool = True
    class Config:
        orm_mode = True

class DocumentBase(BaseModel):
    pass

class Document(DocumentBase):
    id: int
    filename: str
    status: str
    created_at: datetime
    signers: List[Signer] = []
    fields: List[Field] = []
    class Config:
        orm_mode = True
