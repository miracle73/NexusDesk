from fastapi import APIRouter

from app.api.routes import auth, chat, conversations, documents

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"],
)
