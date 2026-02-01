import uuid
import os
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .users import get_current_user
from ..services import storage

router = APIRouter()

@router.post("/upload", response_model=schemas.Document)
async def upload_document(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    
    # Upload file using storage layer
    file_path = await storage.upload_file(file.file, unique_filename, "uploads")
    
    # Create DB entry
    db_document = models.Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        status=models.DocumentStatus.DRAFT
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

@router.get("/", response_model=list[schemas.Document])
def list_documents(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Document).filter(models.Document.user_id == current_user.id).all()

@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(models.Document).filter(models.Document.id == document_id, models.Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Determine which file to serve
    file_path = document.file_path
    filename = document.filename
    
    if document.status == models.DocumentStatus.COMPLETED:
        # Try to get signed version
        signed_filename = f"signed_{document.id}.pdf"
        if storage.IS_VERCEL:
            # In Vercel, check if signed file exists in DB or construct blob URL
            # For now, we'll store signed_path in a separate field or use naming convention
            signed_path = document.file_path.replace(document.filename, signed_filename) if "/" in document.file_path else f"signed_docs/{signed_filename}"
        else:
            signed_path = os.path.join("signed_docs", signed_filename)
            if os.path.exists(signed_path):
                file_path = signed_path
                filename = f"signed_{filename}"
    
    # Download file content
    file_content = await storage.download_file(file_path)
    
    return Response(
        content=file_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/{document_id}/signers", response_model=schemas.Signer)
def add_signer(
    document_id: int,
    signer: schemas.SignerCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(models.Document).filter(models.Document.id == document_id, models.Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate a unique token for signing
    token = str(uuid.uuid4())
    
    db_signer = models.Signer(
        document_id=document_id,
        email=signer.email,
        name=signer.name,
        token=token
    )
    db.add(db_signer)
    db.commit()
    db.refresh(db_signer)

    # Add default signature field at top right (e.g. x=450, y=700 approx for letter)
    # Most PDFs are ~600x800 pts. 
    default_field = models.Field(
        document_id=document_id,
        signer_id=db_signer.id,
        page_number=1,
        x_coordinate=450, 
        y_coordinate=750,
        type=models.FieldType.SIGNATURE,
        include_name=True,
        include_date=True
    )
    db.add(default_field)
    db.commit()

    return db_signer

@router.post("/{document_id}/fields", response_model=schemas.Field)
def add_field(
    document_id: int,
    field: schemas.FieldCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(models.Document).filter(models.Document.id == document_id, models.Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find signer by email in this document
    signer = db.query(models.Signer).filter(models.Signer.document_id == document_id, models.Signer.email == field.signer_email).first()
    if not signer:
        raise HTTPException(status_code=400, detail="Signer not found in this document")

    # Check if field already exists for this signer and document (update if exists)
    db_field = db.query(models.Field).filter(models.Field.document_id == document_id, models.Field.signer_id == signer.id).first()
    
    if db_field:
        db_field.page_number = field.page_number
        db_field.x_coordinate = field.x_coordinate
        db_field.y_coordinate = field.y_coordinate
        db_field.type = field.type
        db_field.include_name = field.include_name
        db_field.include_date = field.include_date
    else:
        db_field = models.Field(
            document_id=document_id,
            signer_id=signer.id,
            page_number=field.page_number,
            x_coordinate=field.x_coordinate,
            y_coordinate=field.y_coordinate,
            type=field.type,
            include_name=field.include_name,
            include_date=field.include_date
        )
        db.add(db_field)
    
    db.commit()
    db.refresh(db_field)
    return db_field

@router.post("/{document_id}/send")
def send_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(models.Document).filter(models.Document.id == document_id, models.Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status != models.DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Document already sent")
    
    document.status = models.DocumentStatus.SENT
    
    # Create audit log
    audit = models.AuditLog(
        document_id=document_id,
        action="SENT",
        ip_address="127.0.0.1", # Mock IP
        user_agent="System" # Mock UA
    )
    db.add(audit)
    db.commit()
    
    # "Send" emails (mock)
    signers = db.query(models.Signer).filter(models.Signer.document_id == document_id).all()
    links = []
    for s in signers:
        # Link points to the frontend now
        link = f"http://localhost:8000/?signing_token={s.token}"
        links.append({"email": s.email, "link": link})
        print(f"SENDING EMAIL TO {s.email}: {link}")
    
    return {"message": "Document sent", "links": links}
