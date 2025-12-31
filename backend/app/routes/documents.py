import os
import asyncio
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import aiofiles

from app.database import get_db
from app.models import Document, ProcessingStatus
from app.schemas import DocumentResponse, DocumentDetail
from app.services.pdf_processor import extract_text_from_pdf_sync
from app.config import settings

router = APIRouter()


@router.post("/documents")
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    # Configuration
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_CONTENT_TYPES = ["application/pdf"]
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF files are allowed."
        )
    
    # Sanitize filename to prevent path traversal
    # Extract only the base filename, removing any directory components
    safe_filename = Path(file.filename).name
    
    # Reject invalid filenames
    if not safe_filename or safe_filename.startswith('.') or safe_filename.startswith('..'):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Build file path and validate it's within upload directory
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    if not os.path.abspath(file_path).startswith(os.path.abspath(settings.UPLOAD_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    # Stream file to disk with size validation using async file I/O
    # This prevents blocking the event loop during file writes
    file_size = 0
    first_chunk = True
    
    try:
        # Use aiofiles for non-blocking file writes
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(CHUNK_SIZE):
                file_size += len(chunk)
                
                # Enforce size limit
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE} bytes."
                    )
                
                # Validate PDF magic bytes on first chunk
                if first_chunk:
                    if not chunk.startswith(b'%PDF'):
                        raise HTTPException(status_code=400, detail="File is not a valid PDF")
                    first_chunk = False
                
                # Non-blocking write
                await f.write(chunk)
        
        # Offload CPU-intensive PDF processing to a separate process
        # This prevents blocking the async event loop during PDF parsing
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor() as pool:
            text_content, page_count = await loop.run_in_executor(
                pool,
                extract_text_from_pdf_sync,
                file_path
            )
        
        # Save document to database
        document = Document(
            filename=safe_filename,
            content=text_content,
            file_size=file_size,
            page_count=page_count,
        )
        db.add(document)
        await db.flush()  # Get document.id without committing
        
        processing_status = ProcessingStatus(
            document_id=document.id,
            status="completed",
            processed_at=datetime.utcnow(),
        )
        db.add(processing_status)
        await db.commit()
        await db.refresh(document)
        
        return {"id": document.id, "filename": document.filename}
        
    except HTTPException:
        # Clean up file on validation errors
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        # Clean up file on processing errors
        if os.path.exists(file_path):
            os.remove(file_path)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")



@router.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    # Validate pagination parameters
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 1000:
        raise HTTPException(status_code=400, detail="limit cannot exceed 1000")
    
    # Use eager loading to fetch documents with their processing status in a single query
    # This prevents N+1 queries (1 for documents + N for each status)
    # Apply pagination with offset and limit
    stmt = (
        select(Document)
        .options(selectinload(Document.processing_status))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()

    response = []
    for doc in documents:
        # Access the already-loaded relationship (no additional query)
        status = doc.processing_status
        response.append(
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                page_count=doc.page_count,
                status=status.status if status else "unknown",
                created_at=doc.created_at,
            )
        )

    return response


@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    # Eager load processing_status to avoid separate query
    stmt = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.processing_status))
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Access the already-loaded relationship (no additional query)
    status = document.processing_status

    return DocumentDetail(
        id=document.id,
        filename=document.filename,
        content=document.content,
        file_size=document.file_size,
        page_count=document.page_count,
        status=status.status if status else "unknown",
        created_at=document.created_at,
    )


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    # Eager load processing_status to avoid separate query
    stmt = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.processing_status))
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete the physical file from disk
    file_path = os.path.join(settings.UPLOAD_DIR, document.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            # Log the error but continue with database deletion
            # This ensures the operation is idempotent and database consistency is maintained
            import logging
            logging.error(f"Failed to delete file {file_path}: {e}")

    # Delete from database (cascade will handle the processing_status automatically)
    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted"}

