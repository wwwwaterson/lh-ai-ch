from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document
from app.schemas import SearchResult

router = APIRouter()


@router.get("/search")
async def search_documents(q: str, db: AsyncSession = Depends(get_db)):
    # Use SQLAlchemy ORM with parameterized query to prevent SQL injection
    # The ilike() method safely escapes user input
    stmt = select(Document).where(Document.content.ilike(f"%{q}%"))
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
