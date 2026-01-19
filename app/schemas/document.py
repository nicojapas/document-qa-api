from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from enum import Enum

class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"

class DocumentBase(BaseModel):
    filename: str
    status: DocumentStatus
    created_at: datetime

class DocumentInDB(DocumentBase):
    """Internal MongoDB representation"""
    id: Optional[str] = Field(alias="_id")
    content_type: str
    size: int

    class Config:
        populate_by_name = True

class DocumentResponse(DocumentBase):
    id: str