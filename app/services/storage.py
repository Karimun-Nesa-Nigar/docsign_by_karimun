import os
import io
from typing import BinaryIO, Optional
from fastapi.responses import StreamingResponse

# Check if we're in Vercel environment
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")
IS_VERCEL = BLOB_READ_WRITE_TOKEN is not None

if IS_VERCEL:
    from vercel_blob import put, get, delete as blob_delete

# Local storage directories
LOCAL_UPLOAD_DIR = "uploads"
LOCAL_SIGNED_DIR = "signed_docs"
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)
os.makedirs(LOCAL_SIGNED_DIR, exist_ok=True)

async def upload_file(file_content: BinaryIO, filename: str, folder: str = "uploads") -> str:
    """
    Upload a file to either Vercel Blob (production) or local filesystem (development).
    
    Args:
        file_content: File-like object containing the file data
        filename: Name of the file
        folder: Folder category ('uploads' or 'signed_docs')
    
    Returns:
        str: File path (local) or blob URL (production)
    """
    if IS_VERCEL:
        # Upload to Vercel Blob
        blob_path = f"{folder}/{filename}"
        result = await put(blob_path, file_content, token=BLOB_READ_WRITE_TOKEN)
        return result['url']
    else:
        # Save to local filesystem
        local_dir = LOCAL_UPLOAD_DIR if folder == "uploads" else LOCAL_SIGNED_DIR
        file_path = os.path.join(local_dir, filename)
        
        # Read content and write to file
        content = file_content.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path

async def download_file(file_path: str) -> bytes:
    """
    Download a file from either Vercel Blob (production) or local filesystem (development).
    
    Args:
        file_path: File path (local) or blob URL (production)
    
    Returns:
        bytes: File content
    """
    if IS_VERCEL and file_path.startswith("http"):
        # Download from Vercel Blob
        blob_data = await get(file_path, token=BLOB_READ_WRITE_TOKEN)
        return blob_data
    else:
        # Read from local filesystem
        with open(file_path, "rb") as f:
            return f.read()

async def delete_file(file_path: str) -> bool:
    """
    Delete a file from either Vercel Blob (production) or local filesystem (development).
    
    Args:
        file_path: File path (local) or blob URL (production)
    
    Returns:
        bool: True if successful
    """
    try:
        if IS_VERCEL and file_path.startswith("http"):
            # Delete from Vercel Blob
            await blob_delete(file_path, token=BLOB_READ_WRITE_TOKEN)
        else:
            # Delete from local filesystem
            if os.path.exists(file_path):
                os.remove(file_path)
        return True
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False

def get_file_response(file_path: str, filename: str, media_type: str = "application/pdf"):
    """
    Create a FileResponse or StreamingResponse for file download.
    This is a synchronous wrapper for use in FastAPI routes.
    
    Args:
        file_path: File path (local) or blob URL (production)
        filename: Download filename
        media_type: MIME type
    
    Returns:
        Response object
    """
    if IS_VERCEL and file_path.startswith("http"):
        # For Vercel Blob, we need to use StreamingResponse
        # This will be handled in the route itself
        return None
    else:
        # For local files, use FileResponse
        from fastapi.responses import FileResponse
        return FileResponse(file_path, filename=filename, media_type=media_type)
