import os
import io
from typing import BinaryIO, Optional
from fastapi.responses import StreamingResponse

# Check for production environment
# We use SUPABASE_URL and SUPABASE_KEY to detect if we should use Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IS_PRODUCTION = SUPABASE_URL is not None and SUPABASE_KEY is not None

if IS_PRODUCTION:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Ensure buckets exist (best effort, or do manually)
    try:
        # This might fail if buckets already exist or if we don't have permissions to list
        # But we'll try to use them anyway
        pass 
    except:
        pass

# Local storage directories
LOCAL_UPLOAD_DIR = "uploads"
LOCAL_SIGNED_DIR = "signed_docs"
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)
os.makedirs(LOCAL_SIGNED_DIR, exist_ok=True)

async def upload_file(file_content: BinaryIO, filename: str, folder: str = "uploads") -> str:
    """
    Upload a file to either Supabase Storage (production) or local filesystem (development).
    
    Args:
        file_content: File-like object containing the file data
        filename: Name of the file
        folder: Folder category ('uploads' or 'signed_docs')
    
    Returns:
        str: File path (local) or public URL / path (production)
    """
    if IS_PRODUCTION:
        # Upload to Supabase Storage
        # We use the 'folder' as the bucket name for simplicity, 
        # or we could use a single bucket and folders inside.
        # Let's assume we have a bucket named 'docsign' and we put folders inside.
        # OR better yet, just map 'uploads' -> 'uploads' bucket, 'signed_docs' -> 'signed_docs' bucket
        
        bucket_name = folder
        
        # Read content
        content = file_content.read()
        
        # Supabase expects bytes
        res = supabase.storage.from_(bucket_name).upload(
            path=filename,
            file=content,
            file_options={"content-type": "application/pdf" if filename.endswith(".pdf") else "application/octet-stream", "upsert": "true"}
        )
        
        # Return the public URL or just the path? 
        # The app logic elsewhere seems to expect a path it can download from later.
        # But `download_file` below needs to know how to fetch it.
        # Let's just return the filename/path relative to the bucket for internal consistency,
        # OR return the full public URL if we want to serve it directly.
        # existing logic allows passing the returned string back to download_file.
        
        return f"{bucket_name}/{filename}"
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
    Download a file from either Supabase (production) or local filesystem (development).
    
    Args:
        file_path: File path (local) or 'bucket/filename' (production)
    
    Returns:
        bytes: File content
    """
    if IS_PRODUCTION:
        # Parse bucket and filename
        # We stored it as "bucket_name/filename"
        try:
            slash_index = file_path.find('/')
            if slash_index == -1:
                 raise Exception("Invalid file path format for production")
                 
            bucket_name = file_path[:slash_index]
            filename = file_path[slash_index+1:]
            
            response = supabase.storage.from_(bucket_name).download(filename)
            return response
        except Exception as e:
            print(f"Error downloading from Supabase: {e}")
            return b""
            
    else:
        # Read from local filesystem
        # Ensure we don't try to read a production path locally
        if "/" in file_path and not os.path.exists(file_path):
             # Maybe it's a prod path lingering in DB?
             # Fallback or error
             pass
             
        with open(file_path, "rb") as f:
            return f.read()

async def delete_file(file_path: str) -> bool:
    """
    Delete a file.
    """
    try:
        if IS_PRODUCTION:
            slash_index = file_path.find('/')
            if slash_index != -1:
                bucket_name = file_path[:slash_index]
                filename = file_path[slash_index+1:]
                supabase.storage.from_(bucket_name).remove([filename])
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
        return True
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False
