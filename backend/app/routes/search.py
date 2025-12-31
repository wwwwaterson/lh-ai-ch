from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document
from app.schemas import SearchResult

router = APIRouter()


@router.get("/search")
async def search_documents(
    q: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    # Validate search query first
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # Validate pagination parameters
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    if limit > 1000:
        raise HTTPException(status_code=400, detail="limit cannot exceed 1000")

    stmt = (
        select(Document)
        .where(Document.content.ilike(f"%{q}%"))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()

    results = []
    for doc in documents:
        content = doc.content or ""
        snippet = content[:200] + "..." if len(content) > 200 else content
        results.append(
            SearchResult(
                id=doc.id,
                filename=doc.filename,
                snippet=snippet,
            )
        )

    return results
