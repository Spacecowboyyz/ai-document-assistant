from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    message: str = Field(default="Document uploaded and indexed successfully")


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    created_at: datetime


class DeleteResponse(BaseModel):
    doc_id: str
    deleted: bool
    message: str = Field(default="Document and index removed")
