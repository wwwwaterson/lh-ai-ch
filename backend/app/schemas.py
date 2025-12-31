from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    filename: str


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    status: str
    created_at: datetime
    tags: List[TagResponse] = []  # Include tags in document response

    class Config:
        from_attributes = True


class DocumentDetail(DocumentResponse):
    content: Optional[str] = None


class SearchResult(BaseModel):
    id: int
    filename: str
    snippet: str


class AddTagsRequest(BaseModel):
    tags: List[str] = Field(..., min_items=1, max_items=10)

