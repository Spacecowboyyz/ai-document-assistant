from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    doc_id: str = Field(..., min_length=1)


class SourceDocument(BaseModel):
    page_number: int
    source_filename: str
    content: str


class StreamToken(BaseModel):
    token: str
    done: bool = False
    sources: list[SourceDocument] | None = None


class ChatSyncResponse(BaseModel):
    answer: str
    sources: list[SourceDocument] = []
