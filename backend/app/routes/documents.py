import os
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, ProcessingStatus
from app.schemas import DocumentResponse, DocumentDetail
from app.services.pdf_processor import extract_text_from_pdf
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
    from pathlib import Path
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
    
    # Stream file to disk with size validation
    # This avoids loading the entire file into memory
    file_size = 0
    first_chunk = True
    
    try:
        with open(file_path, "wb") as f:
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
                
                f.write(chunk)
        
        # Process PDF to extract text
        text_content, page_count = await extract_text_from_pdf(file_path)
        
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
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document))
    documents = result.scalars().all()

    response = []
    for doc in documents:
        status_result = await db.execute(
            select(ProcessingStatus).where(ProcessingStatus.document_id == doc.id)
        )
        status = status_result.scalar_one_or_none()
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
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    status_result = await db.execute(
        select(ProcessingStatus).where(ProcessingStatus.document_id == document.id)
    )
    status = status_result.scalar_one_or_none()

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
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    status_result = await db.execute(
        select(ProcessingStatus).where(ProcessingStatus.document_id == document.id)
    )
    status = status_result.scalar_one_or_none()
    if status:
        await db.delete(status)

    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted"}
