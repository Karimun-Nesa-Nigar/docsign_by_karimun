import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.responses import FileResponse
from .. import models, schemas
from ..database import get_db
from ..services import pdf_service

router = APIRouter()

SIGNED_DOCS_DIR = "signed_docs"
os.makedirs(SIGNED_DOCS_DIR, exist_ok=True)

@router.get("/download/{token}")
def download_signed_by_token(token: str, db: Session = Depends(get_db)):
    signer = db.query(models.Signer).filter(models.Signer.token == token).first()
    if not signer:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    document = signer.document
    if document.status != models.DocumentStatus.COMPLETED:
        # If not fully signed, let them download original for now? 
        # Or just say "Processing"? 
        # Usually they want the final signed version.
        # Let's return original if not finished, or signed if done.
        return FileResponse(document.file_path, filename=document.filename, media_type="application/pdf")

    signed_path = os.path.join(SIGNED_DOCS_DIR, f"signed_{document.id}.pdf")
    if os.path.exists(signed_path):
         return FileResponse(signed_path, filename=f"signed_{document.filename}", media_type="application/pdf")
    
    return FileResponse(document.file_path, filename=document.filename, media_type="application/pdf")

class SignatureSubmission(BaseModel):
    signature_data: str # Base64 image string

@router.get("/sign/{token}")
def view_document_for_signing(token: str, db: Session = Depends(get_db)):
    signer = db.query(models.Signer).filter(models.Signer.token == token).first()
    if not signer:
        raise HTTPException(status_code=404, detail="Invalid signing link")
    
    document = signer.document
    fields = [f for f in document.fields if f.signer_id == signer.id]
    
    return {
        "document_id": document.id,
        "filename": document.filename,
        "signer_name": signer.name,
        "fields": fields
    }

@router.post("/sign/{token}")
def sign_document(token: str, submission: SignatureSubmission, request: Request, db: Session = Depends(get_db)):
    signer = db.query(models.Signer).filter(models.Signer.token == token).first()
    if not signer:
        raise HTTPException(status_code=404, detail="Invalid signing link")
    
    if signer.has_signed:
         raise HTTPException(status_code=400, detail="Already signed")
         
    signer.has_signed = True
    signer.signed_at = datetime.utcnow()
    
    # Store signature data temporarily in signer record? Or just trust it burns in now?
    # Ideally should store signature image in DB/Filesystem relative to Signer. 
    # For this simplified demo, we will persist it in a memory dict or temp file, 
    # OR better yet, we just burn it immediately if all complete. 
    # BUT, if others haven't signed, we lose this guy's signature if we don't save it.
    
    # Let's save the signature image to disk for the signer
    sig_filename = f"sig_{signer.id}_{signer.token}.png"
    sig_path = os.path.join(SIGNED_DOCS_DIR, sig_filename)
    # Actually just write the full base64 string to a text file or just rely on burning at end?
    # If we rely on burning at the end, we MUST save it now.
    with open(sig_path + ".txt", "w") as f:
         f.write(submission.signature_data)
    
    # Log audit
    audit = models.AuditLog(
        document_id=signer.document_id,
        action="SIGNED",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit)
    db.commit()
    
    # Check if all signers have signed
    document = signer.document
    # Refresh to see latest states
    # Note: current transaction is not committed for 'signer.has_signed' yet? 
    # db.commit() has been called above for audit, so yes.
    
    all_signed = all(s.has_signed for s in document.signers)
    
    if all_signed:
        document.status = models.DocumentStatus.COMPLETED
        
        file_path = document.file_path
        output_path = os.path.join(SIGNED_DOCS_DIR, f"signed_{document.id}.pdf")
        
        signatures_to_burn = []
        for s in document.signers:
            # Load saved signature
            s_sig_path = os.path.join(SIGNED_DOCS_DIR, f"sig_{s.id}_{s.token}.png.txt")
            if os.path.exists(s_sig_path):
                with open(s_sig_path, "r") as f:
                    sig_data = f.read()
            else:
                sig_data = None

            user_fields = [f for f in document.fields if f.signer_id == s.id]
            for f in user_fields:
                signatures_to_burn.append({
                    "page_number": f.page_number,
                    "x": f.x_coordinate,
                    "y": f.y_coordinate,
                    "text": f"{s.name}",
                    "image_data": sig_data,
                    "include_name": f.include_name,
                    "include_date": f.include_date,
                    "signed_at": s.signed_at.strftime("%Y-%m-%d %H:%M") if s.signed_at else ""
                })
        
        try:
            pdf_service.sign_pdf(file_path, output_path, signatures_to_burn)
            audit_complete = models.AuditLog(
                document_id=document.id,
                action="COMPLETED",
                ip_address="System",
                user_agent="System"
            )
            db.add(audit_complete)
            db.commit()
        except Exception as e:
            print(f"Error burning PDF: {e}")
            
    db.commit()
    return {"message": "Signed successfully"}
