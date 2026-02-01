import io
import base64
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import tempfile
import os

def sign_pdf(input_path: str, output_path: str, signatures: list):
    """
    signatures: list of dicts with keys: page_number, x, y, text, image_base64
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Group signatures by page
    sigs_by_page = {}
    for sig in signatures:
        p = sig['page_number']
        if p not in sigs_by_page:
            sigs_by_page[p] = []
        sigs_by_page[p].append(sig)

    for i, page in enumerate(reader.pages):
        page_num = i + 1 
        
        if page_num in sigs_by_page:
            packet = io.BytesIO()
            # Dimensions: We assume the doc is close to letter or use arbitrary large canvas
            # Ideally we should get page size from pypdf mediabox
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            
            c = canvas.Canvas(packet, pagesize=(width, height))
            
            for sig in sigs_by_page[page_num]:
                x = float(sig['x'])
                # Docs usually have 0,0 at bottom left.
                # Our frontend probably assumed top-left coords if we weren't careful?
                # For now let's assume coordinates from DB are consistent with PDF coords (bottom-up)
                # But wait, frontend just gave a fixed 100, 200.
                y = float(sig['y'])

                if 'image_data' in sig and sig['image_data']:
                    try:
                        # Decode base64
                        # format: data:image/png;base64,.....
                        header, encoded = sig['image_data'].split(",", 1)
                        img_bytes = base64.b64decode(encoded)
                        
                        # Create temp file for reportlab image
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            tmp.write(img_bytes)
                            tmp_path = tmp.name
                        
                        # Draw image. Size? Let's fix a size.
                        c.drawImage(tmp_path, x, y, width=150, height=50, mask='auto')
                        
                        # Draw extra info below if requested
                        curr_y = y - 10
                        if sig.get('include_name'):
                            c.setFont("Helvetica", 8)
                            c.drawString(x, curr_y, f"Signer: {sig.get('text', '')}")
                            curr_y -= 10
                        
                        if sig.get('include_date'):
                            c.setFont("Helvetica", 8)
                            c.drawString(x, curr_y, f"Date: {sig.get('signed_at', '')}")

                        os.unlink(tmp_path)
                    except Exception as e:
                        print(f"Error drawing image: {e}")
                else:
                    c.drawString(x, y, sig.get('text', ''))
                
            c.save()
            packet.seek(0)
            
            watermark = PdfReader(packet)
            page.merge_page(watermark.pages[0])
        
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

def sign_pdf_bytes(input_pdf_bytes: bytes, signatures: list) -> bytes:
    """
    Same as sign_pdf but works with bytes in memory (for cloud storage).
    
    Args:
        input_pdf_bytes: Original PDF as bytes
        signatures: list of dicts with keys: page_number, x, y, text, image_data, include_name, include_date, signed_at
    
    Returns:
        bytes: Signed PDF as bytes
    """
    reader = PdfReader(io.BytesIO(input_pdf_bytes))
    writer = PdfWriter()

    # Group signatures by page
    sigs_by_page = {}
    for sig in signatures:
        p = sig['page_number']
        if p not in sigs_by_page:
            sigs_by_page[p] = []
        sigs_by_page[p].append(sig)

    for i, page in enumerate(reader.pages):
        page_num = i + 1 
        
        if page_num in sigs_by_page:
            packet = io.BytesIO()
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            
            c = canvas.Canvas(packet, pagesize=(width, height))
            
            for sig in sigs_by_page[page_num]:
                x = float(sig['x'])
                y = float(sig['y'])

                if 'image_data' in sig and sig['image_data']:
                    try:
                        # Decode base64
                        header, encoded = sig['image_data'].split(",", 1)
                        img_bytes = base64.b64decode(encoded)
                        
                        # Create temp file for reportlab image
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            tmp.write(img_bytes)
                            tmp_path = tmp.name
                        
                        # Draw image
                        c.drawImage(tmp_path, x, y, width=150, height=50, mask='auto')
                        
                        # Draw extra info below if requested
                        curr_y = y - 10
                        if sig.get('include_name'):
                            c.setFont("Helvetica", 8)
                            c.drawString(x, curr_y, f"Signer: {sig.get('text', '')}")
                            curr_y -= 10
                        
                        if sig.get('include_date'):
                            c.setFont("Helvetica", 8)
                            c.drawString(x, curr_y, f"Date: {sig.get('signed_at', '')}")

                        os.unlink(tmp_path)
                    except Exception as e:
                        print(f"Error drawing image: {e}")
                else:
                    c.drawString(x, y, sig.get('text', ''))
                
            c.save()
            packet.seek(0)
            
            watermark = PdfReader(packet)
            page.merge_page(watermark.pages[0])
        
        writer.add_page(page)

    # Write to bytes
    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.read()
