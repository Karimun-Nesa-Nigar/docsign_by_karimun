import os
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .. import models, schemas
from ..database import get_db
from ..services import pdf_service, storage

router = APIRouter()

@router.get("/download/{token}")
async def download_signed_by_token(token: str, db: Session = Depends(get_db)):
    signer = db.query(models.Signer).filter(models.Signer.token == token).first()
    if not signer:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    document = signer.document
    file_path = document.file_path
    filename = document.filename
    
    if document.status == models.DocumentStatus.COMPLETED:
        # Try to get signed version
        signed_filename = f"signed_{document.id}.pdf"
        if storage.IS_VERCEL:
            signed_path = document.file_path.replace(os.path.basename(document.file_path), signed_filename) if "/" in document.file_path else f"signed_docs/{signed_filename}"
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
async def sign_document(token: str, submission: SignatureSubmission, request: Request, db: Session = Depends(get_db)):
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
    
    # Save the signature image using storage layer
    sig_filename = f"sig_{signer.id}_{signer.token}.png.txt"
    sig_content = io.BytesIO(submission.signature_data.encode('utf-8'))
    sig_path = await storage.upload_file(sig_content, sig_filename, "signed_docs")
    
    # Store the signature path in the signer for later retrieval
    # For now, we'll reconstruct it when needed
    
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
            # Load saved signature using storage layer
            s_sig_filename = f"sig_{s.id}_{s.token}.png.txt"
            if storage.IS_VERCEL:
                s_sig_path = f"signed_docs/{s_sig_filename}"
            else:
                s_sig_path = os.path.join("signed_docs", s_sig_filename)
            
            try:
                sig_content_bytes = await storage.download_file(s_sig_path)
                sig_data = sig_content_bytes.decode('utf-8')
            except:
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
            # Download original PDF
            original_pdf_bytes = await storage.download_file(file_path)
            
            # Generate signed PDF in memory
            output_pdf_bytes = pdf_service.sign_pdf_bytes(original_pdf_bytes, signatures_to_burn)
            
            # Upload signed PDF
            signed_filename = f"signed_{document.id}.pdf"
            output_pdf_io = io.BytesIO(output_pdf_bytes)
            signed_path = await storage.upload_file(output_pdf_io, signed_filename, "signed_docs")
            
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
