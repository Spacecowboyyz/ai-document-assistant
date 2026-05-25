from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service, get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatSyncResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat/{session_id}")
async def chat_stream(
    session_id: str,
    body: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    service.verify_doc_access(current_user.id, body.doc_id)
    return StreamingResponse(
        service.stream_chat(current_user.id, session_id, body),
        media_type="text/event-stream",
    )


@router.post("/chat/{session_id}/sync", response_model=ChatSyncResponse)
async def chat_sync(
    session_id: str,
    body: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user),
) -> ChatSyncResponse:
    """Non-streaming chat for environments with SSE timeout issues."""
    return await service.chat_sync(current_user.id, session_id, body)
