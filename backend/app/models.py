from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text)
    file_size = Column(Integer)
    page_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    processing_status = relationship(
        "ProcessingStatus",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"  # Automatically delete ProcessingStatus when Document is deleted
    )


class ProcessingStatus(Base):
    __tablename__ = "processing_statuses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    status = Column(String(50), default="completed")
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="processing_status")
